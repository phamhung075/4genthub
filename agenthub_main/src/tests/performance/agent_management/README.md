# Performance Testing for Agent Management System

Comprehensive performance testing suite for the `call_agent` MCP tool with 1000+ concurrent users.

## 📊 Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| First call latency (P95) | < 500ms | ✅ Yes |
| Cached call latency (P95) | < 100ms | ✅ Yes |
| Database query time (P95) | < 50ms | ⚠️ Recommended |
| Error rate | < 1% | ✅ Yes |
| Throughput | > 100 req/s | ⚠️ Recommended |

## 🔧 Test Tools

### Primary: K6 (Recommended)
- **Pros**: Lightweight, JavaScript-based, excellent performance, built-in metrics
- **Cons**: Requires Node.js/Go installation
- **Use for**: Production performance testing, CI/CD integration

### Fallback: Locust (Alternative)
- **Pros**: Python-based, web UI, easy debugging, familiar to Python developers
- **Cons**: Higher resource usage, slower at high concurrency
- **Use for**: Development testing, detailed debugging, Python integration

## 🚀 Quick Start

### Option 1: K6 (Recommended)

```bash
# Install k6
## macOS
brew install k6

## Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

## Windows
choco install k6

# Run performance test
cd agenthub_main/src/tests/performance/agent_management
k6 run k6_call_agent_load_test.js

# Custom configuration
k6 run --vus 1000 --duration 5m k6_call_agent_load_test.js

# Generate JSON report
k6 run k6_call_agent_load_test.js --out json=performance_results.json
```

### Option 2: Locust (Fallback)

```bash
# Install Locust
pip install locust

# Run with web UI (recommended for development)
cd agenthub_main/src/tests/performance/agent_management
locust -f locust_call_agent_load_test.py --host=http://localhost:8000

# Open browser to http://localhost:8089
# Configure: 1000 users, 50 spawn rate, 5 minutes

# Run headless (for CI/CD)
locust -f locust_call_agent_load_test.py \\
       --host=http://localhost:8000 \\
       --users 1000 \\
       --spawn-rate 50 \\
       --run-time 5m \\
       --headless \\
       --html performance_report.html
```

## 📋 Test Scenarios

Both test suites include the following scenarios:

### 1. Ramp-up Test (Main Scenario)
- **Duration**: 8 minutes
- **Pattern**:
  - 0-2min: Ramp 0 → 1000 users
  - 2-7min: Sustain 1000 users
  - 7-8min: Ramp 1000 → 0 users
- **Purpose**: Validate system handles gradual load increase

### 2. Spike Test
- **Duration**: 1 minute
- **Pattern**: Sudden spike to 2000 users
- **Purpose**: Validate system handles sudden traffic bursts

### 3. Soak Test (Optional)
- **Duration**: 1 hour
- **Pattern**: Constant 500 users
- **Purpose**: Identify memory leaks and resource exhaustion

## 📊 Metrics Collected

### Latency Metrics
- **call_agent_latency**: Overall call latency distribution
- **first_call_latency**: Cold start (instance creation) latency
- **cached_call_latency**: Warm call (cached instance) latency
- **database_query_time**: Database operation duration

### Throughput Metrics
- **requests_per_second**: Overall system throughput
- **data_sent/received**: Network bandwidth usage
- **concurrent_users**: Active user count over time

### Reliability Metrics
- **error_rate**: Percentage of failed requests
- **http_req_failed**: HTTP-level failures
- **successful_calls**: Count of successful operations

## 🎯 Running Tests

### Pre-requisites

1. **Backend Running**: Ensure agenthub backend is running
   ```bash
   cd agenthub_main
   python -m fastmcp.server.mcp_entry_point
   ```

2. **Database Ready**: PostgreSQL or SQLite configured
   ```bash
   # Check database connection
   psql -h localhost -U agenthub_user -d agenthub
   ```

3. **Agent Templates Loaded**: Run population script
   ```bash
   python scripts/populate_agent_templates.py
   ```

### Running K6 Tests

```bash
# Standard test (default configuration)
k6 run k6_call_agent_load_test.js

# Custom VUs and duration
k6 run --vus 500 --duration 3m k6_call_agent_load_test.js

# With different target
BASE_URL=http://staging.example.com:8000 k6 run k6_call_agent_load_test.js

# Generate multiple output formats
k6 run k6_call_agent_load_test.js \\
    --out json=results.json \\
    --out influxdb=http://localhost:8086/k6
```

### Running Locust Tests

```bash
# Interactive mode (web UI)
locust -f locust_call_agent_load_test.py --host=http://localhost:8000

# Headless mode with report
locust -f locust_call_agent_load_test.py \\
       --host=http://localhost:8000 \\
       --users 1000 \\
       --spawn-rate 50 \\
       --run-time 5m \\
       --headless \\
       --html report.html \\
       --csv results

# Custom load shape
locust -f locust_call_agent_load_test.py \\
       --host=http://localhost:8000 \\
       --headless \\
       --run-time 10m
```

## 📈 Analyzing Results

### K6 Output

K6 generates a comprehensive summary:

```
✅ ALL TARGETS MET - PERFORMANCE TEST PASSED!

LATENCY METRICS
───────────────────────────────────────────
Overall call_agent latency:
  • P50 (median):  45.23ms
  • P95:           387.45ms ✅
  • P99:           456.78ms

First call (cold start):
  • P95:           412.34ms ✅ (target: <500ms)

Cached call:
  • P95:           67.89ms ✅ (target: <100ms)

THROUGHPUT METRICS
───────────────────────────────────────────
  • Requests/sec:  156.78 req/s
  • Data sent:     12.34 MB
  • Data received: 45.67 MB
```

### Locust Output

Locust provides:
- Real-time web dashboard during test
- HTML report with charts and graphs
- CSV files for custom analysis

### Performance Report JSON

Both tools generate `performance_report.json`:

```json
{
  "timestamp": "2025-11-02T02:00:00Z",
  "test_duration_seconds": 480,
  "total_requests": 75234,
  "latency_metrics": {
    "call_agent_p95": 387.45,
    "first_call_p95": 412.34,
    "cached_call_p95": 67.89
  },
  "performance_targets": {
    "first_call_under_500ms": true,
    "cached_call_under_100ms": true,
    "error_rate_under_1pct": true
  }
}
```

## 🔍 Troubleshooting

### High Latency

**Symptom**: P95 latency > targets

**Diagnosis**:
```bash
# Check database performance
EXPLAIN ANALYZE SELECT * FROM user_agent_instances WHERE user_id = '...';

# Monitor system resources
htop
# or
docker stats
```

**Solutions**:
- Add database indexes
- Enable query caching
- Increase connection pool size
- Optimize ORM queries

### High Error Rate

**Symptom**: Error rate > 1%

**Diagnosis**:
```bash
# Check application logs
tail -f logs/agenthub.log | grep ERROR

# Check database connections
SELECT count(*) FROM pg_stat_activity;
```

**Solutions**:
- Increase max database connections
- Add request rate limiting
- Implement circuit breakers
- Scale horizontally

### Low Throughput

**Symptom**: < 100 req/s with 1000 users

**Diagnosis**:
```bash
# Profile application
py-spy record -o profile.svg --pid <PID>

# Check CPU usage
mpstat -P ALL 1
```

**Solutions**:
- Enable async processing
- Add caching layer (Redis)
- Optimize database queries
- Use CDN for static assets

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on:
  push:
    branches: [main, staging]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup K6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Run Performance Test
        run: |
          cd agenthub_main/src/tests/performance/agent_management
          k6 run k6_call_agent_load_test.js --out json=results.json

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: results.json
```

## 📝 Best Practices

1. **Run tests against staging**: Never run load tests against production
2. **Warm up the system**: Run small test first to warm caches
3. **Monitor infrastructure**: Watch CPU, memory, disk I/O during tests
4. **Baseline comparison**: Compare results against previous runs
5. **Test regularly**: Run performance tests in CI/CD pipeline
6. **Document findings**: Keep performance test results in version control

## 🎯 Success Criteria

Performance test is **PASSED** if:
- ✅ First call P95 latency < 500ms
- ✅ Cached call P95 latency < 100ms
- ✅ Error rate < 1%
- ✅ System remains stable throughout test
- ✅ No memory leaks detected
- ✅ Database connection pool not exhausted

Performance test is **FAILED** if:
- ❌ Any target missed by > 20%
- ❌ Error rate > 5%
- ❌ System crashes or becomes unresponsive
- ❌ Memory usage grows unbounded

## 📚 Additional Resources

- [K6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://martinfowler.com/articles/performance-testing.html)
