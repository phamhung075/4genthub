/**
 * K6 Load Test for call_agent MCP Tool
 *
 * Tests performance of agent instantiation and configuration retrieval
 * with 1000 concurrent users.
 *
 * Performance Targets:
 * - First call (cold start): < 500ms (p95)
 * - Cached call: < 100ms (p95)
 * - Database query performance: < 50ms
 * - Error rate: < 1%
 * - Throughput: > 100 requests/sec
 *
 * Test Scenarios:
 * 1. Ramp-up: 0 → 1000 users over 2 minutes
 * 2. Sustained load: 1000 users for 5 minutes
 * 3. Ramp-down: 1000 → 0 users over 1 minute
 *
 * Usage:
 *   k6 run k6_call_agent_load_test.js
 *   k6 run --vus 1000 --duration 5m k6_call_agent_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend, Rate } from 'k6/metrics';

// ============================================================================
// CONFIGURATION
// ============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const MCP_ENDPOINT = `${BASE_URL}/mcp`;

// Custom metrics
const callAgentLatency = new Trend('call_agent_latency', true);
const firstCallLatency = new Trend('first_call_latency', true);
const cachedCallLatency = new Trend('cached_call_latency', true);
const databaseQueryTime = new Trend('database_query_time', true);
const errorRate = new Rate('error_rate');
const successfulCalls = new Counter('successful_calls');

// ============================================================================
// TEST OPTIONS
// ============================================================================

export const options = {
  scenarios: {
    // Scenario 1: Ramp-up test
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 1000 },  // Ramp up to 1000 users
        { duration: '5m', target: 1000 },  // Stay at 1000 users
        { duration: '1m', target: 0 },     // Ramp down to 0
      ],
      gracefulRampDown: '30s',
    },

    // Scenario 2: Spike test
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 100 },   // Warm up
        { duration: '10s', target: 2000 },  // Spike to 2000 users
        { duration: '30s', target: 2000 },  // Sustain spike
        { duration: '10s', target: 100 },   // Drop back
      ],
      startTime: '9m',  // Start after main test
    },
  },

  thresholds: {
    // Performance thresholds (must meet these or test fails)
    'call_agent_latency': ['p(95)<500'],        // 95% < 500ms
    'first_call_latency': ['p(95)<500'],        // First call < 500ms
    'cached_call_latency': ['p(95)<100'],       // Cached < 100ms
    'database_query_time': ['p(95)<50'],        // DB queries < 50ms
    'error_rate': ['rate<0.01'],                 // Error rate < 1%
    'http_req_failed': ['rate<0.01'],           // HTTP errors < 1%
    'http_req_duration': ['p(95)<1000'],        // Overall < 1s
  },
};

// ============================================================================
// TEST DATA
// ============================================================================

const AGENT_SLUGS = [
  'coding-agent',
  'test-orchestrator-agent',
  'debugger-agent',
  'system-architect-agent',
  'shadcn-ui-expert-agent',
  'security-auditor-agent',
  'documentation-agent',
  'devops-agent',
];

const TEST_USERS = generateTestUsers(100);

function generateTestUsers(count) {
  const users = [];
  for (let i = 0; i < count; i++) {
    users.push({
      id: `user-${i}`,
      email: `perftest${i}@example.com`,
      token: `mock-token-${i}`,
    });
  }
  return users;
}

// ============================================================================
// TEST SCENARIO
// ============================================================================

export default function () {
  const user = TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
  const agentSlug = AGENT_SLUGS[Math.floor(Math.random() * AGENT_SLUGS.length)];

  // Test 1: First call (cold start - creates instance)
  testFirstCall(user, agentSlug);

  sleep(0.5);  // Brief pause between requests

  // Test 2: Cached call (should be faster)
  testCachedCall(user, agentSlug);

  sleep(1);  // Think time between iterations
}

function testFirstCall(user, agentSlug) {
  const payload = {
    jsonrpc: '2.0',
    id: Date.now(),
    method: 'tools/call',
    params: {
      name: 'call_agent',
      arguments: {
        name_agent: agentSlug,
      },
    },
  };

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${user.token}`,
      'X-User-ID': user.id,
    },
    tags: { test_type: 'first_call', agent: agentSlug },
  };

  const startTime = Date.now();
  const response = http.post(MCP_ENDPOINT, JSON.stringify(payload), params);
  const duration = Date.now() - startTime;

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has result': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.result !== undefined;
      } catch {
        return false;
      }
    },
    'latency under 500ms': () => duration < 500,
  });

  if (success) {
    successfulCalls.add(1);
    firstCallLatency.add(duration);
    callAgentLatency.add(duration);

    // Extract database query time from response if available
    try {
      const body = JSON.parse(response.body);
      if (body.result && body.result.performance) {
        databaseQueryTime.add(body.result.performance.db_query_ms || 0);
      }
    } catch (e) {
      // Ignore parsing errors
    }
  } else {
    errorRate.add(1);
  }
}

function testCachedCall(user, agentSlug) {
  const payload = {
    jsonrpc: '2.0',
    id: Date.now(),
    method: 'tools/call',
    params: {
      name: 'call_agent',
      arguments: {
        name_agent: agentSlug,
      },
    },
  };

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${user.token}`,
      'X-User-ID': user.id,
    },
    tags: { test_type: 'cached_call', agent: agentSlug },
  };

  const startTime = Date.now();
  const response = http.post(MCP_ENDPOINT, JSON.stringify(payload), params);
  const duration = Date.now() - startTime;

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'cached response under 100ms': () => duration < 100,
  });

  if (success) {
    cachedCallLatency.add(duration);
    callAgentLatency.add(duration);
  } else {
    errorRate.add(1);
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

export function setup() {
  console.log('🚀 Starting performance test for call_agent MCP tool');
  console.log(`📍 Target: ${BASE_URL}`);
  console.log(`👥 Max concurrent users: 1000`);
  console.log(`⏱️  Test duration: ~8 minutes + spike test`);

  // Warm up the system
  const payload = {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/call',
    params: {
      name: 'call_agent',
      arguments: { name_agent: 'coding-agent' },
    },
  };

  http.post(MCP_ENDPOINT, JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json' },
  });

  console.log('✅ Warmup complete, starting load test...\n');
}

export function teardown(data) {
  console.log('\n📊 Performance test complete!');
  console.log('📈 Check the summary below for detailed metrics');
}

// ============================================================================
// HELPER: Summary Report
// ============================================================================

export function handleSummary(data) {
  const report = {
    timestamp: new Date().toISOString(),
    test_duration_seconds: data.state.testRunDurationMs / 1000,
    total_requests: data.metrics.iterations.values.count,
    successful_requests: data.metrics.successful_calls.values.count,
    failed_requests: data.metrics.http_req_failed.values.count,

    latency_metrics: {
      call_agent_p50: data.metrics.call_agent_latency.values['p(50)'],
      call_agent_p95: data.metrics.call_agent_latency.values['p(95)'],
      call_agent_p99: data.metrics.call_agent_latency.values['p(99)'],
      first_call_p95: data.metrics.first_call_latency.values['p(95)'],
      cached_call_p95: data.metrics.cached_call_latency.values['p(95)'],
      database_query_p95: data.metrics.database_query_time?.values['p(95)'] || 0,
    },

    performance_targets: {
      first_call_under_500ms: data.metrics.first_call_latency.values['p(95)'] < 500,
      cached_call_under_100ms: data.metrics.cached_call_latency.values['p(95)'] < 100,
      error_rate_under_1pct: data.metrics.error_rate.values.rate < 0.01,
    },

    throughput: {
      requests_per_second: data.metrics.iterations.values.rate,
      data_sent_mb: data.metrics.data_sent.values.count / 1024 / 1024,
      data_received_mb: data.metrics.data_received.values.count / 1024 / 1024,
    },
  };

  return {
    'stdout': generateTextReport(report),
    'performance_report.json': JSON.stringify(report, null, 2),
  };
}

function generateTextReport(report) {
  return `
╔══════════════════════════════════════════════════════════════════════════════╗
║                   CALL_AGENT PERFORMANCE TEST REPORT                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

📅 Timestamp: ${report.timestamp}
⏱️  Duration: ${report.test_duration_seconds.toFixed(2)}s
📊 Total Requests: ${report.total_requests}
✅ Successful: ${report.successful_requests}
❌ Failed: ${report.failed_requests}

─────────────────────────────────────────────────────────────────────────────────
LATENCY METRICS
─────────────────────────────────────────────────────────────────────────────────
Overall call_agent latency:
  • P50 (median):  ${report.latency_metrics.call_agent_p50.toFixed(2)}ms
  • P95:           ${report.latency_metrics.call_agent_p95.toFixed(2)}ms ${report.latency_metrics.call_agent_p95 < 500 ? '✅' : '❌'}
  • P99:           ${report.latency_metrics.call_agent_p99.toFixed(2)}ms

First call (cold start):
  • P95:           ${report.latency_metrics.first_call_p95.toFixed(2)}ms ${report.performance_targets.first_call_under_500ms ? '✅' : '❌'} (target: <500ms)

Cached call:
  • P95:           ${report.latency_metrics.cached_call_p95.toFixed(2)}ms ${report.performance_targets.cached_call_under_100ms ? '✅' : '❌'} (target: <100ms)

Database queries:
  • P95:           ${report.latency_metrics.database_query_p95.toFixed(2)}ms ${report.latency_metrics.database_query_p95 < 50 ? '✅' : '❌'} (target: <50ms)

─────────────────────────────────────────────────────────────────────────────────
THROUGHPUT METRICS
─────────────────────────────────────────────────────────────────────────────────
  • Requests/sec:  ${report.throughput.requests_per_second.toFixed(2)} req/s
  • Data sent:     ${report.throughput.data_sent_mb.toFixed(2)} MB
  • Data received: ${report.throughput.data_received_mb.toFixed(2)} MB

─────────────────────────────────────────────────────────────────────────────────
PERFORMANCE TARGETS
─────────────────────────────────────────────────────────────────────────────────
  ${report.performance_targets.first_call_under_500ms ? '✅' : '❌'} First call P95 < 500ms
  ${report.performance_targets.cached_call_under_100ms ? '✅' : '❌'} Cached call P95 < 100ms
  ${report.performance_targets.error_rate_under_1pct ? '✅' : '❌'} Error rate < 1%

═════════════════════════════════════════════════════════════════════════════════
${Object.values(report.performance_targets).every(v => v) ? '✅ ALL TARGETS MET - PERFORMANCE TEST PASSED!' : '❌ SOME TARGETS MISSED - OPTIMIZATION NEEDED'}
═════════════════════════════════════════════════════════════════════════════════
`;
}
