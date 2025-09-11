# Session Hook Auto-Injection Performance Test Suite

Comprehensive performance validation tests for the MCP Session Hook Auto-Injection system implemented in Phase 1. This test suite validates the **40% improvement target** in task completion rate while ensuring token usage remains under 100 tokens per injection.

## 🎯 Performance Targets

| Metric | Target | Validation |
|--------|--------|------------|
| Task Completion Rate Improvement | **40%** | End-to-end workflow comparison |
| Token Usage per Injection | **< 100 tokens** | Context length measurement |
| MCP Query Response Time | **< 500ms** | Individual client performance |
| Token Refresh Time | **< 1000ms** | Authentication flow timing |
| Cache Hit Response Time | **< 10ms** | Cache effectiveness measurement |
| Full Injection Pipeline | **< 2000ms** | Complete auto-injection workflow |
| Cache Hit Rate | **> 80%** | Cache utilization effectiveness |

## 📁 Test Structure

```
performance/
├── __init__.py                 # Performance test configuration
├── PERFORMANCE_TESTS.md        # This documentation
│
├── unit/                       # Individual component tests
│   ├── test_mcp_client_performance.py
│   └── __init__.py
│
├── integration/                # Cross-component interaction tests  
│   ├── test_keycloak_auth_performance.py
│   ├── test_session_hooks_performance.py
│   └── __init__.py
│
├── e2e/                        # Complete workflow tests
│   ├── test_auto_injection_workflow.py
│   └── __init__.py
│
├── benchmarks/                 # Metrics collection & validation
│   ├── performance_suite.py
│   ├── results/               # Generated benchmark reports
│   └── __init__.py
│
└── mocks/                      # Controlled testing environment
    ├── mock_mcp_server.py
    └── __init__.py
```

## 🧪 Test Categories

### Unit Tests (`unit/`)
Tests individual component performance in isolation:

- **TokenManager Performance**: JWT token caching, refresh timing, thread safety
- **RateLimiter Efficiency**: Request throttling accuracy and response times  
- **MCPHTTPClient Response Times**: Basic, resilient, and optimized client performance
- **Cache Performance**: Hit rates, read/write speeds, concurrent access

**Key Test**: `test_mcp_client_performance.py`
```python
# Example: Token cache performance validation
assert avg_cache_time < 0.01  # 10ms max cache operations
assert avg_read_time < 0.005  # 5ms max cache reads
```

### Integration Tests (`integration/`)  
Tests cross-component interactions and workflows:

- **Keycloak Authentication Flow**: Complete auth pipeline timing and reliability
- **Session Hook Integration**: Cache effectiveness in real scenarios
- **40% Improvement Validation**: Task completion rate measurement
- **Context Quality vs Token Usage**: Optimal balance point analysis

**Key Test**: `test_session_hooks_performance.py`
```python
# Example: 40% improvement target validation
improvement_ratio = improved_rate / baseline_rate
assert improvement_ratio >= 1.4  # 40% improvement minimum
```

### End-to-End Tests (`e2e/`)
Tests complete user workflows from session start to task completion:

- **Full Auto-Injection Pipeline**: Complete workflow timing  
- **User Experience Under Load**: Concurrent session handling
- **System Degradation Scenarios**: Behavior under adverse conditions
- **Performance Improvement Measurement**: Real-world impact validation

**Key Test**: `test_auto_injection_workflow.py`
```python
# Example: Complete E2E workflow validation  
assert avg_total_time < PERFORMANCE_CONFIG["response_time_targets"]["full_injection"]
assert avg_tokens < PERFORMANCE_CONFIG["max_tokens_per_injection"]
```

### Benchmarks (`benchmarks/`)
Comprehensive metrics collection and validation system:

- **Performance Suite**: Automated benchmark execution
- **Resource Monitoring**: CPU, memory, and system resource tracking
- **Improvement Validation**: Automated 40% target verification  
- **Report Generation**: Human-readable performance reports

**Key Component**: `performance_suite.py`
```python
# Example: Automated benchmark execution
suite = PerformanceSuite()
results = await suite.run_all_benchmarks()
report = suite.generate_performance_report(results)
```

## 🔧 Mock Testing Environment (`mocks/`)

### MockMCPServer
Provides controlled testing environment with configurable:
- **Response delays**: Simulate network latency
- **Error rates**: Test fallback strategies  
- **Token failure rates**: Validate auth resilience
- **Performance metrics**: Track request statistics

```python
# Example: Create test server with specific behavior
server = create_performance_test_server(
    response_delay=0.1,  # 100ms delay
    error_rate=0.05      # 5% error rate
)
```

## 🚀 Running Performance Tests

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio psutil

# Ensure project dependencies are installed
cd dhafnck_mcp_main
pip install -e .
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest dhafnck_mcp_main/src/tests/performance/unit/ -v -m performance

# Integration tests only  
pytest dhafnck_mcp_main/src/tests/performance/integration/ -v -m performance

# End-to-end tests only
pytest dhafnck_mcp_main/src/tests/performance/e2e/ -v -m performance

# All performance tests
pytest dhafnck_mcp_main/src/tests/performance/ -v -m performance
```

### Run Complete Performance Suite

```bash
# Run comprehensive benchmark suite
cd dhafnck_mcp_main/src/tests/performance/benchmarks
python performance_suite.py

# Or run as module
python -m dhafnck_mcp_main.src.tests.performance.benchmarks.performance_suite
```

### Performance Test Configuration

The test suite uses `PERFORMANCE_CONFIG` for consistent target validation:

```python
PERFORMANCE_CONFIG = {
    "target_improvement": 0.40,        # 40% improvement target
    "max_tokens_per_injection": 100,   # Token usage limit
    "response_time_targets": {
        "mcp_query": 0.5,              # 500ms max
        "token_refresh": 1.0,          # 1s max
        "cache_hit": 0.01,             # 10ms max  
        "full_injection": 2.0          # 2s max
    },
    "cache_hit_rate_target": 0.80,     # 80% cache hit rate
    "test_iterations": 100,            # Statistical significance
    "concurrent_sessions": 10          # Load testing
}
```

## 📊 Performance Metrics & Validation

### Key Performance Indicators (KPIs)

1. **Task Completion Rate Improvement**
   - **Target**: 40% improvement over baseline
   - **Measurement**: Time comparison with/without auto-injection
   - **Validation**: E2E workflow measurement

2. **Token Usage Efficiency**  
   - **Target**: < 100 tokens per injection
   - **Measurement**: Context text length estimation
   - **Validation**: All injection scenarios

3. **Response Time Performance**
   - **MCP Queries**: < 500ms average
   - **Authentication**: < 1000ms token refresh
   - **Cache Operations**: < 10ms hits
   - **Full Pipeline**: < 2000ms end-to-end

4. **System Reliability**
   - **Success Rates**: > 95% under normal conditions
   - **Degradation Handling**: > 80% under adverse conditions
   - **Concurrent Load**: > 90% success with 10+ concurrent sessions

### Automated Validation

The benchmark suite automatically validates all targets:

```python
# Example: Automated target validation
@pytest.mark.performance
def test_performance_targets_met():
    improvement_metric = get_improvement_metric()
    assert improvement_metric.meets_target
    
    token_metric = get_token_usage_metric()
    assert token_metric.value < PERFORMANCE_CONFIG["max_tokens_per_injection"]
```

## 📈 Benchmark Results & Reporting

### Automated Report Generation

The performance suite generates detailed reports:

- **JSON Results**: Machine-readable metrics data
- **Markdown Reports**: Human-readable performance summaries  
- **Target Validation**: Pass/fail status for each metric
- **Trend Analysis**: Performance over time (with historical data)

### Sample Report Output

```
# Performance Validation Report
Generated: 2025-01-XX XX:XX:XX UTC

## Summary
- Total benchmarks: 3
- Successful benchmarks: 3/3
- Benchmarks meeting all targets: 3/3

## Key Performance Targets
- 40% improvement target: 40.0%
- Max tokens per injection: 100
- MCP query response time: 0.5s
- Full injection time: 2.0s

## Benchmark Results
### MCP Client Performance
- Success rate: 98.00%
- All targets met: ✅ Yes

### Session Hook Auto-Injection  
- Success rate: 96.00%
- All targets met: ✅ Yes
- Average token usage: 87.2 (target: 100) ✅

### 40% Improvement Validation
- Success rate: 100.00%
- Total improvement: 42.3% (target: 40.0%) ✅
- Target met: ✅ Yes

## Conclusions
🎉 **All performance targets met!** The Session Hook Auto-Injection system
successfully delivers the targeted performance improvements.
```

## 🔍 Troubleshooting Performance Issues

### Common Performance Issues

1. **Slow MCP Queries**
   - Check network connectivity to MCP server
   - Verify authentication token caching  
   - Review connection pooling configuration

2. **High Token Usage**
   - Reduce context size (fewer tasks, shorter descriptions)
   - Optimize context formatting logic
   - Implement more aggressive caching

3. **Cache Misses** 
   - Verify cache TTL configuration
   - Check cache key generation consistency
   - Review cache invalidation logic

4. **Authentication Delays**
   - Verify Keycloak server responsiveness
   - Check token refresh timing
   - Review credential caching

### Performance Debugging

```python
# Enable detailed performance logging
import logging
logging.getLogger('performance_tests').setLevel(logging.DEBUG)

# Run with resource monitoring
pytest dhafnck_mcp_main/src/tests/performance/ -v -s --log-level=DEBUG

# Profile specific test components
python -m cProfile -s cumtime test_specific_component.py
```

## 🎯 Success Criteria

The Session Hook Auto-Injection system is considered performance-validated when:

- ✅ **40% improvement target met**: Task completion rate shows ≥40% improvement
- ✅ **Token budget respected**: All injections use <100 tokens
- ✅ **Response times acceptable**: All timing targets met consistently  
- ✅ **High reliability**: >95% success rate under normal conditions
- ✅ **Graceful degradation**: >80% success under adverse conditions
- ✅ **Concurrent scalability**: Handles 10+ concurrent sessions effectively

## 📚 Architecture References

- **Implementation**: `.claude/hooks/utils/mcp_client.py`
- **Session Hooks**: `.claude/hooks/session_start.py`  
- **Cache Manager**: `.claude/hooks/utils/cache_manager.py`
- **Service Account**: `dhafnck_mcp_main/src/fastmcp/auth/service_account.py`
- **Task ID**: `91c86fd9-7f74-400e-8720-7f12f799daa3`

---

*This performance test suite ensures the Session Hook Auto-Injection system delivers measurable performance improvements while maintaining system reliability and efficiency.*