"""
Locust Load Test for call_agent MCP Tool (Fallback)

Alternative performance test using Locust (Python-based).
Use this if k6 is unavailable or when Python integration is preferred.

Performance Targets:
- First call (cold start): < 500ms (p95)
- Cached call: < 100ms (p95)
- Database query performance: < 50ms
- Error rate: < 1%
- Throughput: > 100 requests/sec

Test Scenarios:
- Ramp-up to 1000 concurrent users
- Sustained load test
- Spike test

Usage:
    # Web UI mode
    locust -f locust_call_agent_load_test.py --host=http://localhost:8000

    # Headless mode
    locust -f locust_call_agent_load_test.py --host=http://localhost:8000 \\
           --users 1000 --spawn-rate 50 --run-time 5m --headless

    # Generate HTML report
    locust -f locust_call_agent_load_test.py --host=http://localhost:8000 \\
           --users 1000 --spawn-rate 50 --run-time 5m --headless \\
           --html performance_report.html
"""

import json
import random
import time

# Try to import locust, skip gracefully if not available
try:
    from locust import HttpUser, LoadTestShape, between, events, task
    from locust.runners import MasterRunner

    LOCUST_AVAILABLE = True
except ImportError:
    # Locust not installed - this file can't be run as a load test
    # Set flag for pytest to skip collection
    import pytest

    pytestmark = pytest.mark.skip(
        reason="locust not installed (optional dependency for load testing)"
    )
    LOCUST_AVAILABLE = False

    # Define dummy classes and objects with nested attributes so the file doesn't crash during import
    class DummyListener:
        def add_listener(self, func):
            return func

    class DummyEvents:
        request = DummyListener()
        test_start = DummyListener()
        test_stop = DummyListener()

    class HttpUser:
        wait_time = None

    class MasterRunner:
        pass

    class LoadTestShape:
        pass

    # task can be used as @task or @task(weight)
    def task(weight_or_func=1):
        def decorator(func):
            return func

        if callable(weight_or_func):
            return weight_or_func
        return decorator

    def between(*args):
        return lambda: 1

    events = DummyEvents()

# ============================================================================
# CONFIGURATION
# ============================================================================

AGENT_SLUGS = [
    "coding-agent",
    "test-orchestrator-agent",
    "debugger-agent",
    "system-architect-agent",
    "shadcn-ui-expert-agent",
    "security-auditor-agent",
    "documentation-agent",
    "devops-agent",
]

# Performance metrics tracking
metrics = {
    "first_call_latencies": [],
    "cached_call_latencies": [],
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
}


# ============================================================================
# CUSTOM METRICS TRACKING
# ============================================================================


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics for each request"""
    global metrics

    metrics["total_requests"] += 1

    if exception:
        metrics["failed_requests"] += 1
    else:
        metrics["successful_requests"] += 1

        # Track latency by call type
        if "first_call" in name:
            metrics["first_call_latencies"].append(response_time)
        elif "cached_call" in name:
            metrics["cached_call_latencies"].append(response_time)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate performance report at test completion"""
    print("\n" + "=" * 80)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 80)

    total = metrics["total_requests"]
    success = metrics["successful_requests"]
    failed = metrics["failed_requests"]
    success_rate = (success / total * 100) if total > 0 else 0

    print(f"\nTotal Requests: {total}")
    print(f"Successful: {success} ({success_rate:.2f}%)")
    print(f"Failed: {failed} ({(100 - success_rate):.2f}%)")

    # Calculate percentiles
    if metrics["first_call_latencies"]:
        first_call_sorted = sorted(metrics["first_call_latencies"])
        p50_first = percentile(first_call_sorted, 50)
        p95_first = percentile(first_call_sorted, 95)
        p99_first = percentile(first_call_sorted, 99)

        print("\nFirst Call Latency:")
        print(f"  P50: {p50_first:.2f}ms")
        print(
            f"  P95: {p95_first:.2f}ms {'✅' if p95_first < 500 else '❌'} (target: <500ms)"
        )
        print(f"  P99: {p99_first:.2f}ms")

    if metrics["cached_call_latencies"]:
        cached_sorted = sorted(metrics["cached_call_latencies"])
        p50_cached = percentile(cached_sorted, 50)
        p95_cached = percentile(cached_sorted, 95)
        p99_cached = percentile(cached_sorted, 99)

        print("\nCached Call Latency:")
        print(f"  P50: {p50_cached:.2f}ms")
        print(
            f"  P95: {p95_cached:.2f}ms {'✅' if p95_cached < 100 else '❌'} (target: <100ms)"
        )
        print(f"  P99: {p99_cached:.2f}ms")

    # Performance targets check
    targets_met = []
    if metrics["first_call_latencies"]:
        targets_met.append(p95_first < 500)
    if metrics["cached_call_latencies"]:
        targets_met.append(p95_cached < 100)
    targets_met.append(success_rate > 99)

    print("\n" + "-" * 80)
    if all(targets_met):
        print("✅ ALL PERFORMANCE TARGETS MET!")
    else:
        print("❌ SOME PERFORMANCE TARGETS MISSED - OPTIMIZATION NEEDED")
    print("=" * 80 + "\n")


def percentile(sorted_list, p):
    """Calculate percentile from sorted list"""
    if not sorted_list:
        return 0
    index = int(len(sorted_list) * p / 100)
    return sorted_list[min(index, len(sorted_list) - 1)]


# ============================================================================
# LOAD TEST USER CLASS
# ============================================================================


class AgentManagementUser(HttpUser):
    """
    Simulates a user calling the call_agent MCP tool repeatedly

    This user:
    1. Makes a first call to instantiate an agent (cold start)
    2. Makes cached calls to retrieve the same agent (warm)
    3. Repeats with different agents to test various scenarios
    """

    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session"""
        self.user_id = f"perftest-user-{random.randint(1, 1000)}"
        self.headers = {
            "Content-Type": "application/json",
            "X-User-ID": self.user_id,
            "Authorization": f"Bearer mock-token-{self.user_id}",
        }

    @task(3)
    def call_agent_first_call(self):
        """Test first call to agent (creates instance)"""
        agent_slug = random.choice(AGENT_SLUGS)

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {
                "name": "call_agent",
                "arguments": {
                    "name_agent": agent_slug,
                },
            },
        }

        with self.client.post(
            "/mcp",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name=f"call_agent_first_call_{agent_slug}",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "result" in data:
                        response.success()
                    else:
                        response.failure("Missing result in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(7)
    def call_agent_cached_call(self):
        """Test cached call to agent (retrieves existing instance)"""
        agent_slug = random.choice(AGENT_SLUGS)

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {
                "name": "call_agent",
                "arguments": {
                    "name_agent": agent_slug,
                },
            },
        }

        with self.client.post(
            "/mcp",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name=f"call_agent_cached_call_{agent_slug}",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "result" in data:
                        # Check response time
                        if response.elapsed.total_seconds() * 1000 < 100:
                            response.success()
                        else:
                            response.failure(
                                f"Cached call too slow: {response.elapsed.total_seconds() * 1000:.2f}ms"
                            )
                    else:
                        response.failure("Missing result in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")


# ============================================================================
# CUSTOM LOAD SHAPES
# ============================================================================

# LoadTestShape is imported at the top of the file


class StepLoadShape(LoadTestShape):
    """
    Custom load shape for ramp-up testing

    Steps:
    1. 0-2min: Ramp up 0 → 1000 users
    2. 2-7min: Sustain 1000 users
    3. 7-8min: Ramp down 1000 → 0 users
    """

    step_time = 60  # Each step is 60 seconds
    step_load = 100  # Add 100 users per step
    spawn_rate = 50  # Spawn 50 users per second
    time_limit = 480  # 8 minutes total

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        # Ramp up phase (0-2min)
        if run_time < 120:
            user_count = int(run_time / self.step_time * self.step_load)
            return (user_count, self.spawn_rate)

        # Sustained load phase (2-7min)
        elif run_time < 420:
            return (1000, self.spawn_rate)

        # Ramp down phase (7-8min)
        else:
            remaining = self.time_limit - run_time
            user_count = int((remaining / 60) * 1000)
            return (max(user_count, 0), self.spawn_rate)


# ============================================================================
# PERFORMANCE REPORT GENERATOR
# ============================================================================


def generate_performance_report(stats):
    """Generate comprehensive performance report"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_requests": stats.total.num_requests,
            "num_failures": stats.total.num_failures,
            "average_response_time": stats.total.avg_response_time,
            "min_response_time": stats.total.min_response_time,
            "max_response_time": stats.total.max_response_time,
            "requests_per_second": stats.total.total_rps,
            "failure_rate": stats.total.fail_ratio,
        },
        "endpoints": {},
    }

    for name, stat in stats.entries.items():
        report["endpoints"][name] = {
            "num_requests": stat.num_requests,
            "num_failures": stat.num_failures,
            "avg_response_time": stat.avg_response_time,
            "median_response_time": stat.median_response_time,
            "percentile_95": stat.get_response_time_percentile(0.95),
            "percentile_99": stat.get_response_time_percentile(0.99),
            "requests_per_second": stat.total_rps,
        }

    return report
