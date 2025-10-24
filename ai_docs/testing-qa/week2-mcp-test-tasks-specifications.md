# Week 2 MCP Test Implementation Tasks - Detailed Specifications
**Date**: 2025-10-24
**Based On**: Strategic Test Plan 2025-10-24
**Phase**: Week 2 - MCP Protocol & Infrastructure Tests
**Target**: Increase coverage from 65% to 75%
**Total Effort**: 45 hours across 7 tasks

---

## Overview

Week 2 builds on the authentication and database foundation from Week 1 to test the MCP protocol infrastructure, caching layer, and communication transports. These tests ensure system reliability, protocol security, and performance optimization.

**Week 2 Focus Areas**:
- Database migration safety and data preservation
- MCP server startup and graceful degradation
- Client-server communication reliability
- Transport layer protocol handling
- Redis caching hit/miss logic
- Event-based cache invalidation
- Final validation and regression testing

---

## Task 2.1: Database Migration Tests

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: CRITICAL
- **Day**: Day 6 (Monday, Week 2)
- **Estimated Effort**: 6 hours
- **Assignee**: coding-agent
- **Dependencies**: Task 1.8 (Database Initialization Tests) must be complete
- **Coverage Impact**: 0% → 85%

### Component Under Test
- **File**: `agenthub_main/src/fastmcp/database_migrations.py:1-103`
- **Purpose**: Schema evolution via Alembic migrations
- **Lines of Code**: 103
- **Complexity**: Medium-High (schema changes, data migrations)

### Why This Test Matters

#### Security Risk
Schema migrations affect data integrity. Without tests:
- Data corruption during schema changes
- Foreign key constraint violations undetected
- Index corruption leading to query failures
- Rollback failures leave database in inconsistent state

#### Business Impact
Deployments depend on safe migrations. If this fails:
- Production deployments blocked (cannot upgrade)
- Data loss risk (migration failure with no rollback)
- Downtime extended (manual database recovery)
- Customer data corruption (irreversible without backup)

#### Technical Risk
Alembic migrations with complex schema changes. 103 lines managing schema evolution. High-risk operations (ALTER TABLE, DROP COLUMN) need comprehensive testing.

### Test Scenarios to Cover

#### 1. Happy Path - Forward Migration
- **Given**: Database at version N
- **When**: Migration to version N+1 executed
- **Then**: Schema updated, data preserved, indexes created
- **Verification**: Tables exist, columns match schema, data intact

#### 2. Error Scenarios - Migration Failures
- **Edge case 1**: Duplicate migration run → Idempotent, no double-apply
- **Edge case 2**: Missing prerequisite migration → Fails with clear error
- **Edge case 3**: Data constraint violation during migration → Rollback to previous state
- **Failure handling**: All errors rollback transaction

#### 3. Security Scenarios - Data Integrity
- **Invalid input**: Corrupted migration script → Validation fails before execution
- **Unauthorized access**: Only migration system can alter schema → Permission checks
- **Data preservation**: Existing data not lost → Verified after migration

#### 4. Rollback Scenarios - Backward Compatibility
- **Downgrade**: Roll back to previous version successfully
- **Data preservation**: Downgrade doesn't lose data (where possible)
- **Re-upgrade**: Can upgrade again after downgrade

### Test File Location
- **Path**: `agenthub_main/src/tests/integration/test_database_migrations.py`
- **Test Class**: `TestDatabaseMigrations`
- **Dependencies**:
  - Alembic for migration management
  - Test database with migration history
  - Sample data fixtures
  - Migration version tracking

### Acceptance Criteria
- [ ] Forward migrations apply correctly (up migrations work)
- [ ] Backward migrations (rollback) work without data loss
- [ ] Data preserved through migrations (verify with sample data)
- [ ] Idempotent migrations safe to re-run (no duplicate errors)
- [ ] Migration version tracking accurate (alembic_version table)
- [ ] Coverage increases from 0% to 85%+
- [ ] No data loss in any test scenario
- [ ] All tests pass in CI/CD pipeline

### Implementation Notes
```python
# Key test patterns to implement:

# 1. Migration forward test
def test_upgrade_to_head():
    """Verify all migrations can be applied"""
    command.upgrade(alembic_config, "head")
    verify_schema_matches_models()

# 2. Migration backward test
def test_downgrade_to_base():
    """Verify migrations can be rolled back"""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    verify_clean_state()

# 3. Data preservation test
def test_migration_preserves_data():
    """Verify existing data survives migration"""
    insert_test_data()
    command.upgrade(alembic_config, "head")
    verify_test_data_intact()

# 4. Idempotency test
def test_migration_idempotent():
    """Verify re-running same migration is safe"""
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")  # Should not error
```

---

## Task 2.2: MCP Server Startup Tests

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: CRITICAL
- **Day**: Day 7 (Tuesday, Week 2)
- **Estimated Effort**: 5 hours
- **Assignee**: coding-agent
- **Dependencies**: None (can start after Task 2.1)
- **Coverage Impact**: 0% → 80%

### Component Under Test
- **File**: `agenthub_main/src/fastmcp/server/__main__.py`
- **Purpose**: Server initialization and startup orchestration
- **Complexity**: High (multiple dependencies, error handling)

### Why This Test Matters

#### Security Risk
Server startup initializes auth, database connections, MCP protocol. Without tests:
- Server starts with misconfigured auth (open access)
- Database connection leaks
- MCP protocol not properly initialized
- Environment variables not loaded (secrets exposed in logs)

#### Business Impact
Server startup is critical path. If this fails:
- System completely unavailable (100% downtime)
- No user access to any functionality
- Recovery requires manual intervention
- Monitoring alerts may not fire (startup failure)

#### Technical Risk
Startup orchestration with multiple dependencies (database, Keycloak, Redis). Error handling critical for graceful degradation.

### Test Scenarios to Cover

#### 1. Happy Path - Successful Startup
- **Given**: All dependencies available (DB, Keycloak, Redis)
- **When**: Server starts
- **Then**: All services initialized, health check passes
- **Verification**: Server responds, endpoints available

#### 2. Error Scenarios - Dependency Failures
- **Edge case 1**: Database unavailable → Retry logic works or fails gracefully
- **Edge case 2**: Keycloak unavailable → Falls back to local auth
- **Edge case 3**: Redis unavailable → Caching disabled, system still works
- **Failure handling**: Clear error messages logged, graceful degradation

#### 3. Security Scenarios - Safe Initialization
- **Invalid input**: Malformed environment variables → Validation fails before startup
- **Unauthorized access**: Default credentials rejected → Secure defaults enforced
- **Secrets**: No secrets logged during startup → Log sanitization verified

#### 4. Environment Variable Validation
- **Required vars**: DATABASE_URL, AUTH_PROVIDER validated
- **Optional vars**: REDIS_URL, KEYCLOAK_URL handled gracefully
- **Invalid values**: Rejected with clear error messages

### Test File Location
- **Path**: `agenthub_main/src/tests/integration/server/test_server_startup.py`
- **Test Class**: `TestServerStartup`
- **Dependencies**:
  - Mock external services (DB, Keycloak, Redis)
  - Environment variable mocking
  - Health check utilities
  - Log capture for verification

### Acceptance Criteria
- [ ] Server starts successfully with all dependencies available
- [ ] Server starts with missing optional dependencies (Redis)
- [ ] Database unavailable handled (retry or fail gracefully)
- [ ] Keycloak unavailable triggers fallback to local auth
- [ ] Environment variable validation prevents invalid configs
- [ ] Secrets not logged during startup (security check)
- [ ] Health check endpoint returns 200 OK after startup
- [ ] Startup failures logged clearly with actionable messages
- [ ] Coverage increases from 0% to 80%+
- [ ] All tests pass in CI/CD pipeline

### Implementation Notes
```python
# Key test patterns to implement:

# 1. Successful startup test
@pytest.mark.asyncio
async def test_server_starts_successfully():
    """Verify server initializes with all dependencies"""
    with mock_all_dependencies():
        app = create_app()
        assert app is not None
        response = await app.test_client().get('/health')
        assert response.status_code == 200

# 2. Graceful degradation test
@pytest.mark.asyncio
async def test_server_starts_without_redis():
    """Verify server works without Redis"""
    with mock_db_and_keycloak():  # No Redis
        app = create_app()
        assert app is not None
        # Verify caching disabled but system functional

# 3. Environment validation test
def test_missing_required_env_fails():
    """Verify missing DATABASE_URL prevents startup"""
    with clear_environment():
        with pytest.raises(EnvironmentError):
            create_app()

# 4. Secret sanitization test
def test_no_secrets_in_logs(caplog):
    """Verify secrets not logged during startup"""
    with mock_environment(DATABASE_URL="postgres://user:password@host"):
        create_app()
        assert "password" not in caplog.text
```

---

## Task 2.3: MCP Client Connection Tests

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: HIGH
- **Day**: Day 8 (Wednesday, Week 2)
- **Estimated Effort**: 7 hours
- **Assignee**: coding-agent
- **Dependencies**: Task 2.2 (Server Startup) should be complete
- **Coverage Impact**: 0% → 75%

### Component Under Test
- **File**: `agenthub_main/src/fastmcp/client/client.py:1-205`
- **Purpose**: MCP client-server communication
- **Lines of Code**: 205
- **Complexity**: High (protocol, connection management, async operations)

### Why This Test Matters

#### Security Risk
Client-server communication protocol. Without tests:
- Message tampering undetected
- Unauthorized command execution
- Session hijacking via stolen client credentials
- Malformed messages crash server

#### Business Impact
All AI agent communication depends on MCP client. If this fails:
- No agent coordination (100% of AI features broken)
- Task execution blocked
- Real-time updates stopped
- User experience severely degraded

#### Technical Risk
205 lines of protocol handling, connection management, message serialization. Complex async operations with multiple transport types.

### Test Scenarios to Cover

#### 1. Happy Path - Connection Lifecycle
- **Given**: MCP server running
- **When**: Client connects
- **Then**: Handshake completes, commands can be sent
- **Verification**: Connection established, messages exchange

#### 2. Error Scenarios - Connection Issues
- **Edge case 1**: Server unavailable → Retry with exponential backoff
- **Edge case 2**: Connection dropped mid-request → Reconnect and retry
- **Edge case 3**: Malformed server response → Parse error handled gracefully
- **Failure handling**: All errors logged with context, operations retried

#### 3. Security Scenarios - Protocol Security
- **Invalid input**: Malformed commands rejected by client validation
- **Unauthorized access**: Invalid auth token rejected before sending
- **Message integrity**: Tampered messages detected and rejected

#### 4. Command Sending Tests
- **Successful command**: Request sent, response received correctly
- **Command timeout**: Long-running command times out gracefully
- **Concurrent commands**: Multiple commands handled correctly

### Test File Location
- **Path**: `agenthub_main/src/tests/integration/client/test_mcp_client.py`
- **Test Class**: `TestMCPClient`
- **Dependencies**:
  - Mock MCP server (or test server instance)
  - Message fixtures (valid/invalid requests)
  - Connection mocking utilities
  - Async test support (pytest-asyncio)

### Acceptance Criteria
- [ ] Client connects to server successfully (handshake complete)
- [ ] Client sends commands and receives responses
- [ ] Server unavailable triggers retry with backoff
- [ ] Connection dropped mid-request handled (reconnect)
- [ ] Malformed server responses parsed safely
- [ ] Invalid commands rejected before sending
- [ ] Invalid auth tokens prevent connection
- [ ] Message integrity verification works
- [ ] Concurrent commands handled correctly
- [ ] Coverage increases from 0% to 75%+
- [ ] All tests pass in CI/CD pipeline

### Implementation Notes
```python
# Key test patterns to implement:

# 1. Connection test
@pytest.mark.asyncio
async def test_client_connects(mock_mcp_server):
    """Verify client establishes connection"""
    client = MCPClient(server_url="http://localhost:8000")
    await client.connect()
    assert client.is_connected()

# 2. Command sending test
@pytest.mark.asyncio
async def test_client_sends_command(mock_mcp_server):
    """Verify client sends command successfully"""
    client = MCPClient(server_url="http://localhost:8000")
    await client.connect()
    response = await client.send_command("task_create", {"title": "Test"})
    assert response["success"] is True

# 3. Connection failure test
@pytest.mark.asyncio
async def test_server_unavailable_retries():
    """Verify retry logic on server unavailable"""
    client = MCPClient(server_url="http://unavailable:9999")
    with pytest.raises(ConnectionError):
        await client.connect(max_retries=3, backoff=0.1)

# 4. Message validation test
@pytest.mark.asyncio
async def test_malformed_command_rejected():
    """Verify malformed commands rejected"""
    client = MCPClient(server_url="http://localhost:8000")
    await client.connect()
    with pytest.raises(ValueError):
        await client.send_command("", {})  # Invalid command
```

---

## Task 2.4: MCP Transport Layer Tests

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: MEDIUM
- **Day**: Day 9 (Thursday, Week 2)
- **Estimated Effort**: 8 hours
- **Assignee**: coding-agent
- **Dependencies**: Task 2.3 (Client Connection) should be complete
- **Coverage Impact**: 0% → 65%

### Component Under Test
- **File**: `agenthub_main/src/fastmcp/client/transports.py:1-307`
- **Purpose**: Multiple transport protocols (Stdio, SSE, WebSocket)
- **Lines of Code**: 307
- **Complexity**: Very High (3 different protocols, serialization)

### Why This Test Matters

#### Security Risk
Multiple transport protocols with different security models. Without tests:
- WebSocket hijacking possible
- SSE message injection vulnerabilities
- Stdio buffer overflow risks
- Protocol downgrade attacks

#### Business Impact
Communication reliability. If this fails:
- Intermittent connection drops
- Message loss (tasks not executed)
- Real-time updates delayed
- User experience degraded but system recoverable

#### Technical Risk
307 lines managing 3 different transport types. Complex serialization, connection management, and error handling per transport.

### Test Scenarios to Cover

#### 1. Happy Path - Stdio Transport
- **Given**: Stdio transport selected
- **When**: Client sends message
- **Then**: Message sent via stdin/stdout successfully
- **Verification**: Message serialized correctly

#### 2. Happy Path - SSE Transport
- **Given**: SSE transport selected
- **When**: Server sends event
- **Then**: Client receives event in real-time
- **Verification**: Event stream established

#### 3. Happy Path - WebSocket Transport
- **Given**: WebSocket transport selected
- **When**: Bidirectional communication occurs
- **Then**: Messages sent and received
- **Verification**: WebSocket connection maintained

#### 4. Error Scenarios - Transport Failures
- **Edge case 1**: Transport unavailable → Falls back to next transport
- **Edge case 2**: Message too large → Chunking or clear error
- **Edge case 3**: Connection timeout → Retry with exponential backoff
- **Failure handling**: All transport errors logged

#### 5. Security Scenarios - Protocol Security
- **Protocol downgrade**: Prevented (no fallback to insecure)
- **Message authentication**: Per transport type
- **Connection encryption**: WSS for WebSocket verified

#### 6. Transport Selection Tests
- **Config-based**: Transport selected from configuration
- **Auto-detection**: Best transport chosen automatically
- **Fallback**: Graceful fallback to available transport

### Test File Location
- **Path**: `agenthub_main/src/tests/integration/client/test_mcp_transports.py`
- **Test Class**: `TestMCPTransports`
- **Dependencies**:
  - Mock transports or test server with all transports
  - Message fixtures for each transport
  - Async test support
  - WebSocket test utilities

### Acceptance Criteria
- [ ] Stdio transport sends/receives messages correctly
- [ ] SSE transport establishes event stream
- [ ] WebSocket transport bidirectional communication works
- [ ] Transport selection based on config works
- [ ] Transport unavailable triggers fallback
- [ ] Message too large handled (chunking or error)
- [ ] Connection timeout triggers retry with backoff
- [ ] Protocol downgrade prevented (security)
- [ ] Message integrity verified per transport
- [ ] Coverage increases from 0% to 65%+
- [ ] All tests pass in CI/CD pipeline

### Implementation Notes
```python
# Key test patterns to implement:

# 1. Stdio transport test
@pytest.mark.asyncio
async def test_stdio_transport():
    """Verify Stdio transport sends/receives"""
    transport = StdioTransport()
    await transport.connect()
    response = await transport.send({"command": "ping"})
    assert response["command"] == "pong"

# 2. SSE transport test
@pytest.mark.asyncio
async def test_sse_transport():
    """Verify SSE transport receives events"""
    transport = SSETransport(url="http://localhost:8000/events")
    await transport.connect()
    event = await transport.receive()
    assert event["type"] == "update"

# 3. WebSocket transport test
@pytest.mark.asyncio
async def test_websocket_transport():
    """Verify WebSocket bidirectional communication"""
    transport = WebSocketTransport(url="ws://localhost:8000/ws")
    await transport.connect()
    await transport.send({"command": "subscribe"})
    message = await transport.receive()
    assert message["status"] == "subscribed"

# 4. Transport fallback test
@pytest.mark.asyncio
async def test_transport_fallback():
    """Verify fallback to next transport on failure"""
    client = MCPClient(transports=["websocket", "sse", "stdio"])
    # Mock websocket unavailable
    await client.connect()
    # Should fall back to SSE
    assert client.active_transport == "sse"

# 5. Message size limit test
@pytest.mark.asyncio
async def test_message_too_large():
    """Verify large message handling"""
    transport = StdioTransport()
    large_message = {"data": "x" * 10_000_000}  # 10MB
    with pytest.raises(MessageTooLargeError):
        await transport.send(large_message)
```

---

## Task 2.5: Redis Cache Decorator Tests

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: MEDIUM
- **Day**: Day 10 AM (Friday, Week 2)
- **Estimated Effort**: 5 hours
- **Assignee**: coding-agent
- **Dependencies**: None (independent task)
- **Coverage Impact**: 0% → 70%

### Component Under Test
- **File**: `agenthub_main/src/fastmcp/server/cache/redis_cache_decorator.py:1-180`
- **Purpose**: Function result caching with Redis
- **Lines of Code**: 180
- **Complexity**: High (decorator pattern, TTL, key management)

### Why This Test Matters

#### Security Risk
Cache poisoning could serve stale/malicious data. Without tests:
- Expired data served (security token expiry bypass)
- Cache key collisions (user A sees user B's data)
- Memory exhaustion (no eviction testing)

#### Business Impact
Performance optimization. If this fails:
- Slow response times (no caching benefit)
- Increased database load
- Degraded user experience
- But system still functional (not critical)

#### Technical Risk
180 lines of caching logic with key management, TTL handling, serialization. Complex decorator pattern with async support.

### Test Scenarios to Cover

#### 1. Happy Path - Cache Hit
- **Given**: Function decorated with @redis_cache
- **When**: Function called twice with same arguments
- **Then**: First call hits DB, second call hits cache
- **Verification**: Function only executed once

#### 2. Happy Path - Cache Miss
- **Given**: Function decorated with @redis_cache
- **When**: Function called with different arguments
- **Then**: Both calls execute function (cache miss)
- **Verification**: Function executed twice

#### 3. Error Scenarios - Cache Failures
- **Edge case 1**: Redis unavailable → Falls back to direct DB call
- **Edge case 2**: Serialization error → Returns uncached result
- **Edge case 3**: Cache key collision → Namespacing prevents collision
- **Failure handling**: All Redis errors caught, logged

#### 4. TTL Scenarios - Time-based Expiry
- **TTL expiry**: Cached item expires after TTL → Revalidation
- **Manual invalidation**: Cache cleared on demand
- **Cache cleanup**: Old entries removed after TTL expires

#### 5. Performance Scenarios
- **Cache hit time**: < 10ms (fast retrieval)
- **Cache miss time**: Function execution time (no slowdown)
- **Memory limits**: Eviction policy works (LRU)

### Test File Location
- **Path**: `agenthub_main/src/tests/unit/cache/test_redis_cache_decorator.py`
- **Test Class**: `TestRedisCacheDecorator`
- **Dependencies**:
  - Mock Redis client (fakeredis)
  - Time mocking (freezegun)
  - Async test support

### Acceptance Criteria
- [ ] Cache hit returns cached value (function not re-executed)
- [ ] Cache miss executes function (first call)
- [ ] Different arguments create different cache keys
- [ ] TTL expiry triggers revalidation (fresh data fetched)
- [ ] Redis unavailable falls back to direct DB call
- [ ] Serialization errors handled gracefully
- [ ] Cache key collision prevented (namespacing)
- [ ] Manual cache invalidation works
- [ ] Memory limits and eviction tested (LRU)
- [ ] Coverage increases from 0% to 70%+
- [ ] All tests pass in CI/CD pipeline

### Implementation Notes
```python
# Key test patterns to implement:

# 1. Cache hit test
@pytest.mark.asyncio
async def test_cache_hit(mock_redis):
    """Verify second call uses cache"""
    call_count = 0

    @redis_cache(ttl=300)
    async def expensive_function(arg):
        nonlocal call_count
        call_count += 1
        return f"result-{arg}"

    result1 = await expensive_function("test")
    result2 = await expensive_function("test")

    assert result1 == result2
    assert call_count == 1  # Only called once

# 2. Cache miss test
@pytest.mark.asyncio
async def test_cache_miss_different_args():
    """Verify different arguments miss cache"""
    @redis_cache(ttl=300)
    async def func(arg):
        return f"result-{arg}"

    result1 = await func("arg1")
    result2 = await func("arg2")

    assert result1 != result2

# 3. TTL expiry test
@pytest.mark.asyncio
@freeze_time("2025-10-24 12:00:00")
async def test_cache_ttl_expiry(mock_redis):
    """Verify cache expires after TTL"""
    call_count = 0

    @redis_cache(ttl=300)  # 5 minutes
    async def func():
        nonlocal call_count
        call_count += 1
        return "result"

    await func()

    # Fast forward past TTL
    with freeze_time("2025-10-24 12:06:00"):  # 6 minutes later
        await func()

    assert call_count == 2  # Called twice, cache expired

# 4. Redis unavailable test
@pytest.mark.asyncio
async def test_redis_unavailable_fallback():
    """Verify fallback to direct call on Redis failure"""
    @redis_cache(ttl=300)
    async def func():
        return "result"

    # Mock Redis unavailable
    with patch('redis.asyncio.Redis', side_effect=ConnectionError):
        result = await func()
        assert result == "result"  # Still works
```

---

## Task 2.6: Cache Invalidation Hooks Tests

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: MEDIUM
- **Day**: Day 10 PM (Friday, Week 2)
- **Estimated Effort**: 4 hours
- **Assignee**: coding-agent
- **Dependencies**: Task 2.5 (Cache Decorator) should be complete
- **Coverage Impact**: 0% → 70%

### Component Under Test
- **File**: `agenthub_main/src/fastmcp/server/cache/cache_invalidation_hooks.py:1-158`
- **Purpose**: Event-driven cache invalidation
- **Lines of Code**: 158
- **Complexity**: Medium-High (event system, pattern matching)

### Why This Test Matters

#### Security Risk
Stale cache serving outdated permissions/data. Without tests:
- User permissions not refreshed after role change
- Deleted data still visible via cache
- Inconsistent state across services

#### Business Impact
Data consistency. If this fails:
- Users see outdated information
- Permission changes not effective immediately
- Support tickets increase
- But no data loss (queries eventually consistent)

#### Technical Risk
158 lines of event-driven cache invalidation. Complex hook system with pattern matching, wildcards, and cascading invalidation.

### Test Scenarios to Cover

#### 1. Happy Path - Entity Update Invalidation
- **Given**: Cached data for entity (user:123)
- **When**: Entity updated event fired
- **Then**: Cache cleared, next read fetches fresh data
- **Verification**: Cache key removed

#### 2. Pattern Matching - Wildcard Invalidation
- **Pattern**: "user:*" invalidates all user caches
- **Pattern**: "task:123:*" invalidates task and subtasks
- **Pattern mismatch**: Doesn't clear unrelated caches
- **Verification**: Correct keys invalidated

#### 3. Error Scenarios - Hook Failures
- **Edge case 1**: Invalid event pattern → Ignored safely
- **Edge case 2**: Redis unavailable during invalidation → Logged but doesn't crash
- **Edge case 3**: Circular invalidation → Prevented by depth limit
- **Failure handling**: All errors caught, logged

#### 4. Cascading Invalidation
- **Scenario**: Update parent invalidates children
- **Safety**: Depth limit prevents infinite loops
- **Verification**: All related caches cleared

### Test File Location
- **Path**: `agenthub_main/src/tests/unit/cache/test_cache_invalidation_hooks.py`
- **Test Class**: `TestCacheInvalidationHooks`
- **Dependencies**:
  - Mock Redis client
  - Event fixtures
  - Pattern matching utilities

### Acceptance Criteria
- [ ] Entity update event clears correct cache
- [ ] Pattern matching with wildcards works correctly
- [ ] Pattern mismatch doesn't clear unrelated caches
- [ ] Invalid event patterns ignored safely
- [ ] Redis unavailable logged but doesn't crash
- [ ] Circular invalidation prevented (depth limit)
- [ ] Cascading invalidation clears related caches
- [ ] Manual invalidation works (admin tools)
- [ ] Coverage increases from 0% to 70%+
- [ ] All tests pass in CI/CD pipeline

### Implementation Notes
```python
# Key test patterns to implement:

# 1. Entity update invalidation test
@pytest.mark.asyncio
async def test_invalidate_on_entity_update(mock_redis):
    """Verify cache cleared on entity update"""
    manager = CacheInvalidationManager()
    cache_key = "user:123"
    mock_redis.set(cache_key, "cached_value")

    await manager.handle_event("user_updated", {"user_id": "123"})

    cached = mock_redis.get(cache_key)
    assert cached is None

# 2. Wildcard pattern test
def test_wildcard_pattern_matching():
    """Verify wildcard invalidates multiple keys"""
    manager = CacheInvalidationManager()

    assert manager.match_pattern("user:*", "user:123") is True
    assert manager.match_pattern("user:*", "task:123") is False

# 3. Cascading invalidation test
@pytest.mark.asyncio
async def test_cascading_invalidation(mock_redis):
    """Verify parent update invalidates children"""
    manager = CacheInvalidationManager()
    mock_redis.set("task:123", "parent")
    mock_redis.set("task:123:subtask:1", "child")

    await manager.handle_event("task_updated", {"task_id": "123"})

    assert mock_redis.get("task:123") is None
    assert mock_redis.get("task:123:subtask:1") is None

# 4. Circular invalidation prevention test
@pytest.mark.asyncio
async def test_circular_invalidation_prevented():
    """Verify circular invalidation doesn't infinite loop"""
    manager = CacheInvalidationManager(max_depth=5)

    # Set up circular dependency
    manager.register_hook("A", invalidate_pattern="B:*")
    manager.register_hook("B", invalidate_pattern="A:*")

    # Should not hang
    await manager.handle_event("A_updated", {})
    # Test completes = no infinite loop
```

---

## Task 2.7: Week 2 Final Review & Validation

### Metadata
- **Task ID**: TBD (assign when creating in MCP system)
- **Priority**: CRITICAL
- **Day**: Day 10 EOD (Friday, Week 2)
- **Estimated Effort**: 2 hours
- **Assignee**: test-orchestrator-agent
- **Dependencies**: Tasks 2.1-2.6 must be complete
- **Coverage Impact**: Validation only (no new coverage)

### Purpose
Final validation of Week 2 implementation, ensuring all tests pass, coverage targets met, and no regressions introduced.

### Activities to Perform

#### 1. Full Regression Suite Run
- **Action**: Execute ALL tests (Week 1 + Week 2)
- **Expected**: 0 failures, 0 regressions
- **Command**: `pytest agenthub_main/src/tests/ --cov --cov-report=html`
- **Verification**: Review coverage report HTML

#### 2. Coverage Validation
- **Target**: 75% overall coverage achieved
- **Breakdown**:
  - Database: 85%+ (migrations, init)
  - MCP Server: 80%+ (startup, client)
  - MCP Transport: 65%+ (stdio, SSE, websocket)
  - Caching: 70%+ (decorator, invalidation)
- **Tool**: Coverage report shows percentages per module

#### 3. Security Review
- **Focus**: MCP protocol tests (server, client, transports)
- **Check**: No security vulnerabilities in test scenarios
- **Reviewer**: Security team (2 hours)
- **Deliverable**: Security sign-off document

#### 4. CI/CD Pipeline Validation
- **Action**: Trigger full CI/CD pipeline
- **Expected**: All stages pass (lint, test, build)
- **Verification**: Green build status
- **Fix**: Any pipeline issues immediately

#### 5. Documentation Updates
- **Update**: TEST-CHANGELOG.md with Week 2 tests added
- **Update**: Test README with new fixtures/utilities
- **Update**: Coverage report documentation
- **Verify**: All documentation accurate

### Acceptance Criteria
- [ ] Full regression suite passes (0 failures)
- [ ] 75% overall coverage achieved and verified
- [ ] No regressions in Week 1 tests (all still passing)
- [ ] Security review completed and approved
- [ ] CI/CD pipeline passing with new tests
- [ ] TEST-CHANGELOG.md updated with all Week 2 tests
- [ ] Test README updated with fixtures/utilities
- [ ] Coverage report generated and reviewed
- [ ] All blockers resolved before sign-off

### Deliverables
1. **Coverage Report**: HTML report showing 75% coverage
2. **Test Summary**: Count of tests added (Week 2)
3. **Security Sign-off**: Document from security team
4. **CI/CD Status**: Screenshot of green build
5. **Documentation**: Updated TEST-CHANGELOG.md and README

### Implementation Notes
```bash
# Commands to run during validation:

# 1. Full test suite with coverage
pytest agenthub_main/src/tests/ \
    --cov=agenthub_main/src \
    --cov-report=html \
    --cov-report=term \
    -v

# 2. Check coverage percentage
pytest agenthub_main/src/tests/ --cov --cov-report=term | grep TOTAL

# 3. Generate coverage JSON for analysis
pytest agenthub_main/src/tests/ --cov --cov-report=json

# 4. Run only Week 2 tests (for isolation check)
pytest agenthub_main/src/tests/integration/test_database_migrations.py \
       agenthub_main/src/tests/integration/server/test_server_startup.py \
       agenthub_main/src/tests/integration/client/test_mcp_client.py \
       agenthub_main/src/tests/integration/client/test_mcp_transports.py \
       agenthub_main/src/tests/unit/cache/test_redis_cache_decorator.py \
       agenthub_main/src/tests/unit/cache/test_cache_invalidation_hooks.py

# 5. Check for test isolation (random order)
pytest agenthub_main/src/tests/ --random-order

# 6. Performance check (test execution time)
pytest agenthub_main/src/tests/ --durations=10
```

---

## Task Dependencies & Sequencing

### Critical Path
```
Week 1 (Complete) → Task 2.1 (Migrations) → Task 2.2 (Server Startup)
                                          ↓
                          Task 2.3 (Client Connection) → Task 2.4 (Transports)
                                          ↓
                          Task 2.5 (Cache) → Task 2.6 (Invalidation)
                                          ↓
                          Task 2.7 (Final Review & Validation)
```

### Parallel Opportunities
- **Tasks 2.5 and 2.6**: Can start while Tasks 2.3-2.4 in progress (different modules)
- **Task 2.1**: Can start independently (database-focused)
- **Task 2.2**: Requires Task 2.1 complete (server needs migrations working)

### Hard Dependencies
- **Task 2.7**: MUST wait for Tasks 2.1-2.6 complete (final validation)
- **Task 2.3**: Should wait for Task 2.2 (client needs server tested)
- **Task 2.4**: Should wait for Task 2.3 (transports are lower-level than client)

---

## Test Infrastructure Requirements

### Required Test Utilities (Create Before Week 2)
1. **Migration Test Database**:
   - Alembic configuration for test environment
   - Sample data fixtures for migration testing
   - Version tracking utilities

2. **Server Startup Mocks**:
   - Mock Keycloak server (responses)
   - Mock Redis server (fakeredis)
   - Mock database connection

3. **MCP Message Fixtures**:
   - Valid request/response samples
   - Invalid message samples
   - Protocol version variations

4. **Transport Test Utilities**:
   - Mock WebSocket server
   - SSE event stream generator
   - Stdio capture utilities

### Test Data Builders (Extend from Week 1)
- **Migration Builder**: Create test migrations for testing
- **Server Config Builder**: Generate test server configurations
- **Message Builder**: Create MCP protocol messages
- **Cache Key Builder**: Generate test cache keys

---

## Success Metrics & KPIs

### Coverage Metrics
- **Overall**: 65% (Week 1 end) → 75% (Week 2 end)
- **Database**: 0% → 85%
- **MCP Server**: 0% → 80%
- **MCP Client**: 0% → 75%
- **Transport**: 0% → 65%
- **Caching**: 0% → 70%

### Quality Metrics
- **Test Count**: +80 tests (Week 2)
- **Regression Rate**: 0% (no existing tests broken)
- **Test Execution Time**: < 10 minutes (full suite)
- **CI/CD Success Rate**: 100% (all builds pass)

### Security Metrics
- **Security Tests**: 15+ security-focused scenarios
- **Vulnerabilities Found**: Document any found during testing
- **Security Review**: Approved sign-off from security team

---

## Risk Mitigation

### Red Flags (Stop and Address)
1. **Coverage drops below 70%**: Investigate regression
2. **More than 5 tests failing consistently**: Infrastructure issue
3. **Test execution time > 15 minutes**: Performance optimization needed
4. **Security test finds vulnerability**: Full audit required

### Contingency Plans
- **Behind Schedule**: Prioritize Tasks 2.1, 2.2, 2.3 (critical path)
- **Resource Shortage**: Focus on MCP tests, defer caching tests
- **Blocker Found**: Escalate immediately, adjust schedule

---

## Post-Week 2 Next Steps

### Week 3+ Improvements (75% → 85%)
1. **CLI Tests**: Command-line interface testing
2. **Edge Cases**: Boundary conditions and rare scenarios
3. **Performance Tests**: Load testing, stress testing
4. **E2E Tests**: Full user workflows
5. **Property-Based Testing**: Hypothesis framework

### Continuous Improvement
- **Monthly Coverage Review**: Track trends, adjust targets
- **Mutation Testing**: Verify test quality (not just coverage)
- **Coverage Gates**: CI/CD fails if coverage drops below 75%
- **Test Maintenance**: Refactor flaky tests, improve speed

---

## Summary

**Week 2 delivers comprehensive MCP infrastructure testing**, ensuring:
- ✅ Database migrations are safe and data-preserving
- ✅ Server startup is robust with graceful degradation
- ✅ Client-server communication is reliable and secure
- ✅ Transport protocols handle all failure modes
- ✅ Caching optimizes performance without data consistency issues
- ✅ Cache invalidation keeps data fresh and secure

**Coverage Impact**: 65% → 75% (+10% overall)
**Risk Reduction**: HIGH (MCP protocol security validated)
**Business Value**: HIGH (system reliability and performance)

**Ready for implementation with clear specifications, acceptance criteria, and success metrics.**
