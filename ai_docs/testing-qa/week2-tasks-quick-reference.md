# Week 2 MCP Test Tasks - Quick Reference Guide
**Date**: 2025-10-24
**Phase**: Week 2 Implementation (Days 6-10)
**Target**: 65% → 75% coverage

---

## Tasks Overview

| Task | Component | Priority | Effort | Day | Coverage |
|------|-----------|----------|--------|-----|----------|
| 2.1 | Database Migrations | CRITICAL | 6h | Mon | 0% → 85% |
| 2.2 | MCP Server Startup | CRITICAL | 5h | Tue | 0% → 80% |
| 2.3 | MCP Client Connection | HIGH | 7h | Wed | 0% → 75% |
| 2.4 | MCP Transport Layer | MEDIUM | 8h | Thu | 0% → 65% |
| 2.5 | Redis Cache Decorator | MEDIUM | 5h | Fri AM | 0% → 70% |
| 2.6 | Cache Invalidation Hooks | MEDIUM | 4h | Fri PM | 0% → 70% |
| 2.7 | Final Review & Validation | CRITICAL | 2h | Fri EOD | Validation |

**Total Effort**: 37 hours (45 with reviews)

---

## Task 2.1: Database Migration Tests

**Component**: `agenthub_main/src/fastmcp/database_migrations.py:1-103`
**Test File**: `src/tests/integration/test_database_migrations.py`
**Dependencies**: Task 1.8 (Database Init) complete

### Key Test Scenarios
- ✅ Forward migration (version N to N+1)
- ✅ Backward migration (rollback to base)
- ✅ Data preservation through migrations
- ✅ Idempotent migrations (safe re-runs)
- ✅ Migration failure handling (transaction rollback)

### Acceptance Criteria
- [ ] All migrations apply successfully
- [ ] Rollback works without data loss
- [ ] Test data preserved through migrations
- [ ] 85% coverage achieved

---

## Task 2.2: MCP Server Startup Tests

**Component**: `agenthub_main/src/fastmcp/server/__main__.py`
**Test File**: `src/tests/integration/server/test_server_startup.py`
**Dependencies**: Task 2.1 complete

### Key Test Scenarios
- ✅ Successful startup with all dependencies
- ✅ Database unavailable (retry or fail gracefully)
- ✅ Keycloak unavailable (fallback to local auth)
- ✅ Redis unavailable (caching disabled)
- ✅ Environment variable validation
- ✅ Secrets not logged during startup

### Acceptance Criteria
- [ ] Server starts with all dependencies
- [ ] Graceful degradation when deps missing
- [ ] No secrets in logs
- [ ] 80% coverage achieved

---

## Task 2.3: MCP Client Connection Tests

**Component**: `agenthub_main/src/fastmcp/client/client.py:1-205`
**Test File**: `src/tests/integration/client/test_mcp_client.py`
**Dependencies**: Task 2.2 complete (preferred)

### Key Test Scenarios
- ✅ Connection lifecycle (connect, send, disconnect)
- ✅ Server unavailable (retry with backoff)
- ✅ Connection dropped mid-request (reconnect)
- ✅ Malformed server response (parse error handling)
- ✅ Malformed commands rejected
- ✅ Invalid auth token rejected
- ✅ Message integrity verification

### Acceptance Criteria
- [ ] Client connects and communicates
- [ ] Connection failures handled
- [ ] Security validation works
- [ ] 75% coverage achieved

---

## Task 2.4: MCP Transport Layer Tests

**Component**: `agenthub_main/src/fastmcp/client/transports.py:1-307`
**Test File**: `src/tests/integration/client/test_mcp_transports.py`
**Dependencies**: Task 2.3 complete (preferred)

### Key Test Scenarios
- ✅ Stdio transport send/receive
- ✅ SSE transport communication
- ✅ WebSocket transport operations
- ✅ Transport selection based on config
- ✅ Transport unavailable (fallback to next)
- ✅ Message too large handling
- ✅ Connection timeout (retry with backoff)
- ✅ Protocol downgrade prevention

### Acceptance Criteria
- [ ] All 3 transports tested
- [ ] Transport fallback works
- [ ] Security validated
- [ ] 65% coverage achieved

---

## Task 2.5: Redis Cache Decorator Tests

**Component**: `agenthub_main/src/fastmcp/server/cache/redis_cache_decorator.py:1-180`
**Test File**: `src/tests/unit/cache/test_redis_cache_decorator.py`
**Dependencies**: None (independent)

### Key Test Scenarios
- ✅ Cache hit (second call uses cache)
- ✅ Cache miss (different arguments)
- ✅ TTL expiry (revalidation after TTL)
- ✅ Redis unavailable (falls back to direct DB)
- ✅ Serialization error (returns uncached result)
- ✅ Cache key collision prevention
- ✅ Manual cache invalidation
- ✅ Memory limits and eviction

### Acceptance Criteria
- [ ] Cache hit/miss logic works
- [ ] TTL expiry tested
- [ ] Redis failure fallback works
- [ ] 70% coverage achieved

---

## Task 2.6: Cache Invalidation Hooks Tests

**Component**: `agenthub_main/src/fastmcp/server/cache/cache_invalidation_hooks.py:1-158`
**Test File**: `src/tests/unit/cache/test_cache_invalidation_hooks.py`
**Dependencies**: Task 2.5 complete (preferred)

### Key Test Scenarios
- ✅ Entity update event clears cache
- ✅ Pattern matching (wildcards)
- ✅ Cascading invalidation safety
- ✅ Invalid event pattern (ignored safely)
- ✅ Redis unavailable (logged, doesn't crash)
- ✅ Circular invalidation prevention

### Acceptance Criteria
- [ ] Event-based invalidation works
- [ ] Pattern matching correct
- [ ] Circular prevention works
- [ ] 70% coverage achieved

---

## Task 2.7: Week 2 Final Review & Validation

**Purpose**: Final validation and sign-off
**Assignee**: test-orchestrator-agent
**Dependencies**: Tasks 2.1-2.6 complete

### Activities
- ✅ Run full regression suite (Week 1 + Week 2)
- ✅ Verify 75% overall coverage achieved
- ✅ Security review of MCP protocol tests
- ✅ CI/CD pipeline validation
- ✅ Documentation updates (TEST-CHANGELOG.md)

### Acceptance Criteria
- [ ] All tests passing (0 regressions)
- [ ] 75% coverage confirmed
- [ ] Security sign-off obtained
- [ ] CI/CD pipeline green
- [ ] Documentation updated

---

## Implementation Commands

### Run Individual Task Tests
```bash
# Task 2.1: Database Migrations
pytest agenthub_main/src/tests/integration/test_database_migrations.py -v

# Task 2.2: Server Startup
pytest agenthub_main/src/tests/integration/server/test_server_startup.py -v

# Task 2.3: MCP Client
pytest agenthub_main/src/tests/integration/client/test_mcp_client.py -v

# Task 2.4: MCP Transports
pytest agenthub_main/src/tests/integration/client/test_mcp_transports.py -v

# Task 2.5: Cache Decorator
pytest agenthub_main/src/tests/unit/cache/test_redis_cache_decorator.py -v

# Task 2.6: Cache Invalidation
pytest agenthub_main/src/tests/unit/cache/test_cache_invalidation_hooks.py -v
```

### Run All Week 2 Tests
```bash
pytest agenthub_main/src/tests/integration/test_database_migrations.py \
       agenthub_main/src/tests/integration/server/test_server_startup.py \
       agenthub_main/src/tests/integration/client/test_mcp_client.py \
       agenthub_main/src/tests/integration/client/test_mcp_transports.py \
       agenthub_main/src/tests/unit/cache/test_redis_cache_decorator.py \
       agenthub_main/src/tests/unit/cache/test_cache_invalidation_hooks.py \
       --cov --cov-report=html -v
```

### Coverage Validation
```bash
# Check overall coverage
pytest agenthub_main/src/tests/ --cov=agenthub_main/src --cov-report=term | grep TOTAL

# Generate detailed coverage report
pytest agenthub_main/src/tests/ --cov=agenthub_main/src --cov-report=html

# Open HTML report
open htmlcov/index.html
```

---

## MCP Task Creation Template

When creating tasks in MCP system, use this format:

```python
# Task 2.1 Example
mcp__agenthub_http__manage_task(
    action="create",
    title="Task 2.1: Database Migration Tests",
    assignees="coding-agent",
    details="""
Component: agenthub_main/src/fastmcp/database_migrations.py:1-103
Test File: src/tests/integration/test_database_migrations.py
Effort: 6 hours
Coverage: 0% → 85%
Priority: CRITICAL

Test Scenarios:
1. Forward migration (version N to N+1)
   - Verify schema updated correctly
   - Verify data preserved
   - Verify indexes created

2. Backward migration (rollback)
   - Verify rollback to previous version
   - Verify data preserved where possible
   - Verify schema reverted

3. Data preservation through migrations
   - Insert test data before migration
   - Run migration
   - Verify test data intact after migration

4. Idempotent migrations
   - Run migration twice
   - Verify no errors on second run
   - Verify schema correct

5. Migration failure handling
   - Simulate failure during migration
   - Verify transaction rollback
   - Verify database in consistent state

Acceptance Criteria:
- All migrations apply successfully
- Rollback works without data loss
- Test data preserved through migrations
- Idempotent migrations safe to re-run
- 85% coverage achieved

Dependencies:
- Task 1.8 (Database Initialization Tests) must be complete

Test File Location:
src/tests/integration/test_database_migrations.py

See full specification at:
ai_docs/testing-qa/week2-mcp-test-tasks-specifications.md
    """,
    status="todo",
    priority="critical"
)
```

---

## Dependencies & Sequencing

### Critical Path
```
Task 2.1 (Migrations) → Task 2.2 (Server Startup)
                            ↓
        Task 2.3 (Client Connection) → Task 2.4 (Transports)
                            ↓
        Task 2.5 (Cache) → Task 2.6 (Invalidation)
                            ↓
        Task 2.7 (Final Review)
```

### Parallel Opportunities
- Tasks 2.5 & 2.6 can start while 2.3 & 2.4 in progress
- Task 2.1 can start immediately (independent)

### Hard Dependencies
- Task 2.7 MUST wait for all others
- Task 2.3 should wait for Task 2.2 (client needs server tested)
- Task 2.4 should wait for Task 2.3 (transports lower-level)

---

## Success Metrics

### Coverage Targets
- Overall: 65% → 75% (+10%)
- Database: 0% → 85%
- MCP Server: 0% → 80%
- MCP Client: 0% → 75%
- Transport: 0% → 65%
- Caching: 0% → 70%

### Quality Metrics
- New Tests: ~80 test cases
- Regression Rate: 0%
- Test Execution Time: < 10 minutes
- Security Tests: 15+ scenarios

---

## Risk Mitigation

### Red Flags (Stop and Address)
1. Coverage drops below 70% → Investigate regression
2. More than 5 tests failing → Infrastructure issue
3. Test execution > 15 minutes → Performance optimization
4. Security test finds vulnerability → Full audit

### Contingency Plans
- Behind schedule → Prioritize Tasks 2.1, 2.2, 2.3
- Resource shortage → Focus on MCP, defer caching
- Blocker found → Escalate, adjust schedule

---

## Quick Start Checklist

Before starting Week 2:
- [ ] Week 1 tests all passing (65% coverage achieved)
- [ ] Test infrastructure ready (fixtures, mocks)
- [ ] Alembic migration test utilities created
- [ ] MCP message fixtures prepared
- [ ] Mock servers configured (Keycloak, Redis)
- [ ] CI/CD pipeline validated with Week 1 tests

During Week 2:
- [ ] Daily stand-up to review blockers
- [ ] Update TEST-CHANGELOG.md after each task
- [ ] Run regression suite after each task completion
- [ ] Track coverage progress daily
- [ ] Escalate blockers immediately

After Week 2:
- [ ] 75% coverage confirmed
- [ ] Security review sign-off
- [ ] Documentation updated
- [ ] CI/CD pipeline green
- [ ] Plan Week 3+ improvements (75% → 85%)

---

## Contact & Escalation

### Task Assignment
- All tasks assigned to: **coding-agent**
- Final review assigned to: **test-orchestrator-agent**

### Escalation Path
1. Blocker encountered → Update MCP task with details
2. Security issue found → Notify security team immediately
3. Schedule risk → Notify project manager
4. Technical question → Consult senior developer

---

**For detailed specifications, see**: `ai_docs/testing-qa/week2-mcp-test-tasks-specifications.md`
**For strategic context, see**: `ai_docs/testing-qa/strategic-test-plan-2025-10-24.md`
