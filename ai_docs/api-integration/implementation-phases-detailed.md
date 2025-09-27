# Detailed Implementation Phases & Steps

## 📋 Implementation Overview
**Duration**: 4 weeks (20 working days)
**Team Size**: 2-3 developers
**Risk Level**: Medium (existing system modifications)

---

## 🚀 PHASE 1: Backend Foundation
**Duration**: 5 days
**Goal**: Establish database and API infrastructure

### Day 1-2: Database Optimization
#### Step 1.1: Create Materialized Views
```sql
-- Location: migrations/2025_01_create_materialized_views.sql

-- Step 1: Create branch_summaries materialized view
CREATE MATERIALIZED VIEW branch_summaries AS
SELECT
    b.id,
    b.project_id,
    b.name,
    b.created_at,
    COUNT(t.id) as total_tasks,
    SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as active_tasks,
    AVG(t.progress_percentage) as avg_progress
FROM branches b
LEFT JOIN tasks t ON t.git_branch_id = b.id
GROUP BY b.id;

-- Step 2: Create indexes
CREATE INDEX idx_branch_summaries_project ON branch_summaries(project_id);
CREATE INDEX idx_branch_summaries_updated ON branch_summaries(last_updated);

-- Step 3: Create refresh function
CREATE OR REPLACE FUNCTION refresh_branch_summary()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY branch_summaries;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Attach triggers
CREATE TRIGGER task_changes_trigger
AFTER INSERT OR UPDATE OR DELETE ON tasks
FOR EACH STATEMENT EXECUTE FUNCTION refresh_branch_summary();
```

**Testing Checklist**:
- [ ] Materialized view creates successfully
- [ ] Triggers fire on task changes
- [ ] Performance improvement measured (target: 70% faster)
- [ ] Concurrent refresh works without blocking

#### Step 1.2: Setup Redis Cache
```python
# Location: agenthub_main/src/infrastructure/cache.py

import redis.asyncio as redis
from typing import Optional, Any
import json

class CacheManager:
    def __init__(self):
        self.redis = redis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )

    async def get_summaries(self, key: str) -> Optional[dict]:
        """Get cached summaries"""
        data = await self.redis.get(f"summaries:{key}")
        return json.loads(data) if data else None

    async def set_summaries(
        self,
        key: str,
        data: dict,
        ttl: int = 300
    ):
        """Cache summaries with TTL"""
        await self.redis.setex(
            f"summaries:{key}",
            ttl,
            json.dumps(data)
        )

    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache by pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

### Day 3-4: Bulk API Endpoint
#### Step 1.3: Implement Bulk Summary Endpoint
```python
# Location: agenthub_main/src/fastmcp/api/v2/branches.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
import hashlib

router = APIRouter(prefix="/api/v2")

@router.post("/branches/summaries/bulk")
async def get_bulk_summaries(
    project_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache)
):
    """
    Implementation steps:
    1. Generate cache key from parameters
    2. Check cache
    3. Query materialized view if cache miss
    4. Transform data
    5. Cache results
    6. Return response
    """

    # Step 1: Generate cache key
    cache_key = hashlib.md5(
        f"{project_ids}:{user_id}:{include_archived}".encode()
    ).hexdigest()

    # Step 2: Check cache
    cached = await cache.get_summaries(cache_key)
    if cached:
        return cached

    # Step 3: Query database
    query = """
        SELECT * FROM branch_summaries
        WHERE project_id = ANY($1)
        AND ($2 OR NOT archived)
    """

    results = await db.execute(
        query,
        project_ids or [],
        include_archived
    )

    # Step 4: Transform results
    response = {
        "summaries": {row.id: row for row in results},
        "metadata": {
            "count": len(results),
            "cached": False,
            "timestamp": datetime.utcnow()
        }
    }

    # Step 5: Cache results
    await cache.set_summaries(cache_key, response)

    return response
```

**Testing Steps**:
1. Unit test with mock data
2. Integration test with real database
3. Load test with 100+ projects
4. Cache hit/miss verification
5. Error handling validation

### Day 5: Cascade Logic
#### Step 1.4: Implement Cascade Calculator
```python
# Location: agenthub_main/src/domain/services/cascade_service.py

class CascadeCalculator:
    """Calculate affected entities from a change"""

    async def calculate_task_cascade(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Dict[str, List]:
        """
        Task change affects:
        1. Parent task (if exists)
        2. Branch summary
        3. Project metrics
        4. Related contexts
        """
        cascade = {
            "tasks": [],
            "branches": [],
            "projects": [],
            "contexts": []
        }

        # Get task details
        task = await db.get(Task, task_id)
        if not task:
            return cascade

        # 1. Parent task
        if task.parent_id:
            parent = await db.get(Task, task.parent_id)
            cascade["tasks"].append(parent.to_summary())

        # 2. Branch summary
        branch_summary = await self.get_branch_summary(
            task.git_branch_id, db
        )
        cascade["branches"].append(branch_summary)

        # 3. Project metrics
        project = await self.get_project_metrics(
            task.project_id, db
        )
        cascade["projects"].append(project)

        return cascade
```

**Validation Checklist**:
- [ ] Task → Branch cascade works
- [ ] Subtask → Parent task cascade works
- [ ] Branch → Project cascade works
- [ ] No infinite loops
- [ ] Performance < 50ms per calculation

---

## 🔌 PHASE 2: WebSocket Protocol
**Duration**: 5 days
**Goal**: Implement real-time communication layer

### Day 6-7: Protocol Implementation
#### Step 2.1: Define Message Protocol
```python
# Location: agenthub_main/src/websocket/protocol.py

from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any
from datetime import datetime
import uuid

class WSMessage(BaseModel):
    """WebSocket message protocol v2.0"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: Literal["2.0"] = "2.0"
    type: Literal["update", "bulk", "sync", "heartbeat"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: int

    payload: Dict[str, Any]
    metadata: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CascadePayload(BaseModel):
    """Cascade update payload"""
    entity: Literal["task", "branch", "project", "subtask"]
    action: Literal["create", "update", "delete"]
    data: Dict[str, Any]
    cascade: Optional[Dict[str, List]] = None
```

#### Step 2.2: WebSocket Server Setup
```python
# Location: agenthub_main/src/websocket/server.py

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from collections import defaultdict
import json

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self.ai_batch_queue = asyncio.Queue()
        self.sequence_counter = 0

    async def connect(self, websocket: WebSocket, user_id: str):
        """Establish WebSocket connection"""
        await websocket.accept()
        self.connections[user_id] = websocket

        # Send initial sync
        await self.send_initial_sync(user_id)

    async def send_initial_sync(self, user_id: str):
        """Send initial data sync on connection"""
        # Get user's projects and branches
        summaries = await get_user_summaries(user_id)

        message = WSMessage(
            type="sync",
            sequence=self.get_next_sequence(),
            payload={
                "summaries": summaries,
                "timestamp": datetime.utcnow()
            },
            metadata={"userId": user_id}
        )

        await self.send_to_user(user_id, message)
```

### Day 8: Batching System
#### Step 2.3: Implement AI Update Batching
```python
# Location: agenthub_main/src/websocket/batching.py

class BatchProcessor:
    """Process AI updates in batches"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.batch_interval = 0.5  # 500ms
        self.max_batch_size = 50

    async def start(self):
        """Start batch processing loop"""
        while True:
            await self.process_batch()
            await asyncio.sleep(0.05)  # Check every 50ms

    async def process_batch(self):
        """Collect and process a batch of updates"""
        batch = []
        deadline = time.time() + self.batch_interval

        # Collect updates until deadline or max size
        while time.time() < deadline and len(batch) < self.max_batch_size:
            try:
                timeout = deadline - time.time()
                if timeout <= 0:
                    break

                message = await asyncio.wait_for(
                    self.manager.ai_batch_queue.get(),
                    timeout=timeout
                )
                batch.append(message)
            except asyncio.TimeoutError:
                break

        if batch:
            merged = self.merge_batch(batch)
            await self.manager.broadcast(merged)

    def merge_batch(self, batch: List[WSMessage]) -> WSMessage:
        """Merge multiple updates into one"""
        merged_cascade = defaultdict(list)
        primary_updates = []

        for msg in batch:
            primary_updates.append(msg.payload["data"]["primary"])

            # Merge cascade data
            if cascade := msg.payload["data"].get("cascade"):
                for key, items in cascade.items():
                    merged_cascade[key].extend(items)

        # Deduplicate cascade items
        for key in merged_cascade:
            seen = set()
            unique = []
            for item in merged_cascade[key]:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    unique.append(item)
            merged_cascade[key] = unique

        return WSMessage(
            type="bulk",
            sequence=self.manager.get_next_sequence(),
            payload={
                "updates": primary_updates,
                "cascade": dict(merged_cascade)
            },
            metadata={"source": "mcp-ai", "batchSize": len(batch)}
        )
```

### Day 9-10: Testing & Error Handling
#### Step 2.4: WebSocket Testing Suite
```python
# Location: tests/websocket/test_protocol.py

import pytest
from fastapi.testclient import TestClient
import asyncio

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection establishment"""
    client = TestClient(app)

    with client.websocket_connect("/ws/test-user") as websocket:
        # Should receive initial sync
        data = websocket.receive_json()
        assert data["type"] == "sync"
        assert "summaries" in data["payload"]

@pytest.mark.asyncio
async def test_ai_batching():
    """Test AI update batching"""
    manager = ConnectionManager()
    processor = BatchProcessor(manager)

    # Send 10 AI updates
    for i in range(10):
        await manager.ai_batch_queue.put(
            create_test_message(f"task-{i}")
        )

    # Wait for batch processing
    await asyncio.sleep(0.6)

    # Should receive 1 bulk message
    assert len(manager.sent_messages) == 1
    assert manager.sent_messages[0]["type"] == "bulk"
    assert len(manager.sent_messages[0]["payload"]["updates"]) == 10

@pytest.mark.asyncio
async def test_cascade_calculation():
    """Test cascade effect calculation"""
    calculator = CascadeCalculator()

    cascade = await calculator.calculate_task_cascade("task-123", db)

    assert "branches" in cascade
    assert "projects" in cascade
    assert len(cascade["branches"]) > 0
```

---

## 🎨 PHASE 3: Frontend Integration
**Duration**: 5 days
**Goal**: Implement client-side state management

### Day 11-12: Redux Setup
#### Step 3.1: Create Redux Store
```typescript
// Location: agenthub-frontend/src/store/store.ts

import { configureStore } from '@reduxjs/toolkit';
import branchReducer from './slices/branchSlice';
import wsMiddleware from './middleware/wsMiddleware';

export const store = configureStore({
  reducer: {
    branches: branchReducer,
    tasks: taskReducer,
    projects: projectReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(wsMiddleware)
});
```

#### Step 3.2: Branch Slice Implementation
```typescript
// Location: agenthub-frontend/src/store/slices/branchSlice.ts

const branchSlice = createSlice({
  name: 'branches',
  initialState: {
    summaries: {} as Record<string, BranchSummary>,
    loading: false,
    error: null,
    lastSync: 0
  },
  reducers: {
    // Bulk load action
    loadSummariesStart(state) {
      state.loading = true;
      state.error = null;
    },

    loadSummariesSuccess(state, action) {
      state.summaries = action.payload.summaries;
      state.lastSync = Date.now();
      state.loading = false;
    },

    // WebSocket update action
    applyWSUpdate(state, action: PayloadAction<WSMessage>) {
      const { payload } = action.payload;

      // Apply primary update
      if (payload.entity === 'branch') {
        state.summaries[payload.data.primary.id] =
          payload.data.primary;
      }

      // Apply cascade updates
      payload.data.cascade?.branches?.forEach(branch => {
        state.summaries[branch.id] = branch;
      });
    }
  }
});
```

### Day 13: WebSocket Client
#### Step 3.3: WebSocket Client Manager
```typescript
// Location: agenthub-frontend/src/services/WebSocketClient.ts

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private aiBuffer: WSMessage[] = [];
  private aiBufferTimer: NodeJS.Timeout | null = null;

  constructor(
    private store: Store,
    private userId: string
  ) {}

  connect() {
    const wsUrl = `${process.env.REACT_APP_WS_URL}/ws/${this.userId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = this.handleOpen.bind(this);
    this.ws.onmessage = this.handleMessage.bind(this);
    this.ws.onerror = this.handleError.bind(this);
    this.ws.onclose = this.handleClose.bind(this);
  }

  private handleMessage(event: MessageEvent) {
    const message: WSMessage = JSON.parse(event.data);

    // Route based on source
    if (message.metadata?.source === 'mcp-ai') {
      this.bufferAIUpdate(message);
    } else {
      this.applyImmediateUpdate(message);
    }
  }

  private bufferAIUpdate(message: WSMessage) {
    this.aiBuffer.push(message);

    // Reset timer
    if (this.aiBufferTimer) {
      clearTimeout(this.aiBufferTimer);
    }

    // Process after 500ms
    this.aiBufferTimer = setTimeout(() => {
      this.processAIBuffer();
    }, 500);
  }

  private processAIBuffer() {
    if (this.aiBuffer.length === 0) return;

    // Merge all updates
    const merged = this.mergeUpdates(this.aiBuffer);

    // Dispatch to store
    this.store.dispatch(
      branchSlice.actions.applyWSUpdate(merged)
    );

    // Clear buffer
    this.aiBuffer = [];
  }
}
```

### Day 14-15: Testing & Polish
#### Step 3.4: Frontend Testing
```typescript
// Location: agenthub-frontend/src/__tests__/websocket.test.ts

describe('WebSocket Integration', () => {
  let wsClient: WebSocketClient;
  let store: Store;
  let mockServer: WS;

  beforeEach(() => {
    mockServer = new WS("ws://localhost:8000/ws/test-user");
    store = createTestStore();
    wsClient = new WebSocketClient(store, 'test-user');
  });

  test('handles user updates immediately', async () => {
    wsClient.connect();
    await mockServer.connected;

    const update = {
      type: 'update',
      metadata: { source: 'user' },
      payload: {
        entity: 'branch',
        data: {
          primary: { id: 'branch-1', name: 'Updated' }
        }
      }
    };

    mockServer.send(JSON.stringify(update));

    // Should update immediately
    expect(store.getState().branches.summaries['branch-1'].name)
      .toBe('Updated');
  });

  test('batches AI updates', async () => {
    wsClient.connect();
    await mockServer.connected;

    // Send 5 AI updates rapidly
    for (let i = 0; i < 5; i++) {
      mockServer.send(JSON.stringify({
        type: 'update',
        metadata: { source: 'mcp-ai' },
        payload: { /* ... */ }
      }));
    }

    // Should not update immediately
    expect(Object.keys(store.getState().branches.summaries))
      .toHaveLength(0);

    // Wait for batch processing
    await new Promise(r => setTimeout(r, 600));

    // Should have all updates
    expect(Object.keys(store.getState().branches.summaries))
      .toHaveLength(5);
  });
});
```

---

## 🧪 PHASE 4: Testing & Deployment
**Duration**: 5 days
**Goal**: Validate, optimize, and deploy

### Day 16-17: Load Testing
#### Step 4.1: Load Test Setup
```python
# Location: tests/load/test_websocket_load.py

import asyncio
import websockets
import json
import time
from typing import List

class LoadTester:
    def __init__(self, base_url: str, num_clients: int):
        self.base_url = base_url
        self.num_clients = num_clients
        self.metrics = {
            "connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "latencies": []
        }

    async def client_session(self, client_id: int):
        """Simulate a client session"""
        url = f"{self.base_url}/ws/user-{client_id}"

        try:
            async with websockets.connect(url) as ws:
                self.metrics["connections"] += 1

                # Send updates
                for i in range(100):
                    start = time.time()

                    message = {
                        "type": "update",
                        "payload": {
                            "entity": "task",
                            "data": {
                                "primary": {
                                    "id": f"task-{client_id}-{i}",
                                    "title": f"Task {i}"
                                }
                            }
                        }
                    }

                    await ws.send(json.dumps(message))
                    self.metrics["messages_sent"] += 1

                    # Wait for response
                    response = await ws.recv()
                    self.metrics["messages_received"] += 1

                    latency = time.time() - start
                    self.metrics["latencies"].append(latency)

                    await asyncio.sleep(0.1)  # 10 updates/second

        except Exception as e:
            self.metrics["errors"] += 1
            print(f"Client {client_id} error: {e}")

    async def run(self):
        """Run load test with all clients"""
        tasks = [
            self.client_session(i)
            for i in range(self.num_clients)
        ]
        await asyncio.gather(*tasks)

        # Calculate statistics
        avg_latency = sum(self.metrics["latencies"]) / len(self.metrics["latencies"])
        p95_latency = sorted(self.metrics["latencies"])[int(len(self.metrics["latencies"]) * 0.95)]

        print(f"""
        Load Test Results:
        - Clients: {self.num_clients}
        - Successful connections: {self.metrics['connections']}
        - Messages sent: {self.metrics['messages_sent']}
        - Messages received: {self.metrics['messages_received']}
        - Errors: {self.metrics['errors']}
        - Avg latency: {avg_latency*1000:.2f}ms
        - P95 latency: {p95_latency*1000:.2f}ms
        """)

# Run test
async def main():
    tester = LoadTester("ws://localhost:8000", num_clients=1000)
    await tester.run()

asyncio.run(main())
```

### Day 18: Performance Optimization
#### Step 4.2: Performance Profiling
```python
# Location: agenthub_main/src/monitoring/profiling.py

from typing import Callable
import time
import cProfile
import pstats
from functools import wraps

def profile_performance(func: Callable):
    """Decorator for performance profiling"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start

        profiler.disable()

        # Log if slow
        if duration > 0.1:  # 100ms threshold
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(10)

            logger.warning(
                f"{func.__name__} took {duration*1000:.2f}ms"
            )

        return result
    return wrapper

# Apply to critical paths
@profile_performance
async def calculate_cascade(task_id: str):
    # ... cascade logic
    pass
```

### Day 19: Migration & Rollout
#### Step 4.3: Migration Script
```python
# Location: scripts/migrate_to_bulk_api.py

import asyncio
from typing import List

class MigrationManager:
    def __init__(self):
        self.old_api = OldAPIClient()
        self.new_api = NewAPIClient()
        self.feature_flags = FeatureFlags()

    async def migrate_gradual(self, percentage: int):
        """Gradual migration with percentage rollout"""
        users = await self.get_all_users()

        # Calculate how many users to migrate
        migrate_count = int(len(users) * (percentage / 100))
        users_to_migrate = users[:migrate_count]

        for user in users_to_migrate:
            await self.feature_flags.enable(
                "USE_BULK_API",
                user.id
            )
            print(f"Migrated user {user.id}")

        print(f"Migrated {migrate_count}/{len(users)} users ({percentage}%)")

    async def rollback(self):
        """Emergency rollback"""
        await self.feature_flags.disable_all("USE_BULK_API")
        print("Rolled back all users to old API")

# Gradual rollout plan
async def main():
    manager = MigrationManager()

    # Day 1: 10% of users
    await manager.migrate_gradual(10)
    await monitor_metrics(hours=24)

    # Day 2: 25% of users
    await manager.migrate_gradual(25)
    await monitor_metrics(hours=24)

    # Day 3: 50% of users
    await manager.migrate_gradual(50)
    await monitor_metrics(hours=24)

    # Day 4: 100% of users
    await manager.migrate_gradual(100)
```

### Day 20: Documentation & Handoff
#### Step 4.4: Complete Documentation
```markdown
# Location: docs/api-optimization-guide.md

## API Optimization Deployment Guide

### Pre-deployment Checklist
- [ ] Database migrations applied
- [ ] Redis cache configured
- [ ] WebSocket server deployed
- [ ] Frontend build with new features
- [ ] Feature flags configured
- [ ] Monitoring dashboards ready
- [ ] Rollback plan documented

### Deployment Steps
1. Deploy backend with feature flags OFF
2. Deploy frontend with backward compatibility
3. Enable features for test users
4. Monitor metrics for 2 hours
5. Gradual rollout (10% → 25% → 50% → 100%)
6. Monitor for 24 hours at each stage

### Monitoring Endpoints
- Health check: GET /health
- Metrics: GET /metrics
- WebSocket stats: GET /ws/stats

### Rollback Procedure
1. Disable feature flags
2. Clear Redis cache
3. Restart WebSocket servers
4. Monitor for stability

### Performance Targets
- Bulk API: < 200ms for 100 branches
- WebSocket latency: < 50ms P95
- Cascade calculation: < 30ms
- Cache hit ratio: > 80%
```

---

## 📊 Success Metrics

### Performance Improvements
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Initial Load | 3 calls × 200ms | 1 call × 200ms | 66% faster |
| Update Latency | 200ms | 50ms | 75% faster |
| Network Traffic | 100KB/update | 60KB/update | 40% reduction |
| Concurrent Users | 500 | 2000 | 4× capacity |

### Business Impact
- **User Experience**: Near real-time updates
- **AI Efficiency**: 60% reduction in token usage
- **System Load**: 50% reduction in API calls
- **Developer Experience**: Simpler state management

## 🚦 Go/No-Go Criteria

### Go Criteria
- ✅ All tests passing (unit, integration, load)
- ✅ Performance targets met
- ✅ No critical bugs in staging
- ✅ Rollback tested successfully
- ✅ Documentation complete

### No-Go Criteria
- ❌ Data inconsistency issues
- ❌ WebSocket stability problems
- ❌ Performance regression > 10%
- ❌ Security vulnerabilities found
- ❌ Incomplete migration tools