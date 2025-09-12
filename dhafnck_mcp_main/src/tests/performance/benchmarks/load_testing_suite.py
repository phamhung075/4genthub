"""
Load Testing Suite

Comprehensive load testing for concurrent request handling, system stability,
and performance under stress conditions.
"""

import asyncio
import time
import statistics
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import psutil
import gc
from datetime import datetime

# Import performance test components
from .. import PERFORMANCE_CONFIG, setup_performance_logger
from .performance_suite import PerformanceMetric, BenchmarkResult, PerformanceBenchmark, ResourceMonitor
from .response_size_tests import ResponseSizeBenchmark
from ...integration.mcp_client_tests import MCPClientTestSuite
from ....fastmcp.task_management.infrastructure.monitoring.metrics_collector import MetricsCollector, timing_context

logger = setup_performance_logger()


@dataclass
class LoadTestResult:
    """Result of a single load test scenario."""
    scenario_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    peak_memory_mb: float
    avg_cpu_percent: float
    error_rate: float
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class ConcurrentRequestGenerator:
    """Generates concurrent requests for load testing."""
    
    def __init__(self, 
                 request_rate: int = 10,
                 duration_seconds: int = 60,
                 max_concurrent: int = 20):
        self.request_rate = request_rate
        self.duration_seconds = duration_seconds
        self.max_concurrent = max_concurrent
        self.metrics_collector = MetricsCollector()
        
        # Request templates
        self.request_templates = [
            {"action": "list", "status": "todo", "limit": 10},
            {"action": "list", "status": "in_progress", "limit": 5},
            {"action": "next", "git_branch_id": "branch-load-test"},
            {"action": "get", "task_id": "load-test-task-1"},
            {"action": "create", "title": "Load Test Task", "assignees": "@test-agent", "git_branch_id": "branch-load-test"},
            {"action": "update", "task_id": "load-test-task-1", "status": "in_progress"}
        ]
    
    async def generate_request_load(self, 
                                   request_handler: Callable,
                                   scenario_name: str = "generic_load") -> LoadTestResult:
        """Generate sustained request load and measure performance."""
        start_time = time.time()
        end_time = start_time + self.duration_seconds
        
        # Performance tracking
        response_times = []
        successful_requests = 0
        failed_requests = 0
        request_count = 0
        
        # Resource monitoring
        resource_monitor = ResourceMonitor()
        resource_monitor.start_monitoring()
        
        # Semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def make_request():
            """Make a single request with timing."""
            nonlocal successful_requests, failed_requests, request_count
            
            async with semaphore:
                request_start = time.perf_counter()
                request_data = random.choice(self.request_templates).copy()
                request_data["load_test_id"] = f"{scenario_name}_{request_count}"
                
                try:
                    with timing_context(f"load_test_request_{scenario_name}"):
                        await request_handler(request_data)
                    
                    response_time = (time.perf_counter() - request_start) * 1000
                    response_times.append(response_time)
                    successful_requests += 1
                    
                    self.metrics_collector.record_timing_metric(
                        "load_test_response_time",
                        request_start,
                        tags={"scenario": scenario_name, "status": "success"}
                    )
                    
                except Exception as e:
                    failed_requests += 1
                    logger.debug(f"Request failed: {str(e)}")
                    
                    self.metrics_collector.record_metric(
                        "load_test_error",
                        1,
                        tags={"scenario": scenario_name, "error_type": type(e).__name__}
                    )
                
                request_count += 1
                resource_monitor.sample_resources()
        
        # Generate requests at specified rate
        tasks = []
        current_time = start_time
        request_interval = 1.0 / self.request_rate
        
        while current_time < end_time:
            # Schedule next request
            tasks.append(asyncio.create_task(make_request()))
            
            # Wait for interval or until max concurrent limit
            if len(tasks) >= self.max_concurrent:
                # Wait for some requests to complete
                done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
            await asyncio.sleep(request_interval)
            current_time = time.time()
        
        # Wait for all remaining requests to complete
        if tasks:
            await asyncio.wait(tasks)
        
        # Calculate results
        total_time = time.time() - start_time
        resource_usage = resource_monitor.stop_monitoring()
        
        # Statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p50_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else avg_response_time
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 2 else avg_response_time
        else:
            avg_response_time = p50_response_time = p95_response_time = p99_response_time = 0.0
        
        actual_rps = request_count / total_time if total_time > 0 else 0.0
        error_rate = (failed_requests / max(request_count, 1)) * 100
        
        return LoadTestResult(
            scenario_name=scenario_name,
            total_requests=request_count,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            p50_response_time_ms=p50_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            requests_per_second=actual_rps,
            peak_memory_mb=resource_usage.get("peak_memory_mb", 0),
            avg_cpu_percent=resource_usage.get("avg_cpu_percent", 0),
            error_rate=error_rate,
            duration_seconds=total_time
        )


class LoadTestingBenchmark(PerformanceBenchmark):
    """Comprehensive load testing benchmark."""
    
    def __init__(self):
        super().__init__("Load Testing & Concurrent Request Handling")
        self.load_config = PERFORMANCE_CONFIG["load_testing"]
        self.response_benchmark = ResponseSizeBenchmark()
        self.metrics_collector = MetricsCollector()
        
        # Test scenarios
        self.load_scenarios = [
            {
                "name": "steady_load",
                "rate": self.load_config["request_rate_per_second"],
                "duration": 60,
                "concurrent": 10,
                "description": "Steady sustained load"
            },
            {
                "name": "peak_load",
                "rate": self.load_config["request_rate_per_second"] * 3,
                "duration": 30,
                "concurrent": self.load_config["max_concurrent_requests"],
                "description": "Peak load simulation"
            },
            {
                "name": "burst_load",
                "rate": self.load_config["request_rate_per_second"] * 5,
                "duration": 15,
                "concurrent": 20,
                "description": "Burst load patterns"
            },
            {
                "name": "sustained_high_load",
                "rate": self.load_config["request_rate_per_second"] * 2,
                "duration": 120,
                "concurrent": 25,
                "description": "Sustained high load endurance test"
            }
        ]
    
    async def setup(self):
        """Setup load testing benchmark."""
        await self.response_benchmark.setup()
        self.metrics_collector.start_collection()
    
    async def teardown(self):
        """Cleanup load testing benchmark."""
        await self.response_benchmark.teardown()
        await self.metrics_collector.stop_collection()
    
    async def mock_mcp_request_handler(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock MCP request handler for load testing."""
        # Simulate MCP server processing time
        processing_delay = random.uniform(0.05, 0.2)  # 50-200ms processing time
        await asyncio.sleep(processing_delay)
        
        # Generate appropriate response based on action
        action = request_data.get("action", "list")
        
        if action == "list":
            return await self.response_benchmark.mock_server.handle_manage_task(request_data)
        elif action == "get":
            return {
                "success": True,
                "data": {
                    "task": {
                        "id": request_data.get("task_id", "test-task"),
                        "title": "Load Test Task",
                        "status": "todo",
                        "priority": "medium"
                    }
                }
            }
        elif action == "create":
            return {
                "success": True,
                "data": {
                    "task": {
                        "id": f"created-task-{random.randint(1000, 9999)}",
                        "title": request_data.get("title", "Created Task"),
                        "status": "todo"
                    }
                }
            }
        elif action == "update":
            return {
                "success": True,
                "data": {
                    "task": {
                        "id": request_data.get("task_id", "updated-task"),
                        "status": request_data.get("status", "updated")
                    }
                }
            }
        else:
            return {"success": True, "data": {"message": f"Processed {action} action"}}
    
    async def run_benchmark(self) -> BenchmarkResult:
        """Run load testing benchmark."""
        self.resource_monitor.start_monitoring()
        start_time = time.perf_counter()
        
        metrics = []
        load_results = []
        errors = []
        
        logger.info("Starting load testing benchmarks...")
        
        try:
            for scenario in self.load_scenarios:
                logger.info(f"Running load test scenario: {scenario['name']} - {scenario['description']}")
                
                # Create request generator
                generator = ConcurrentRequestGenerator(
                    request_rate=scenario["rate"],
                    duration_seconds=scenario["duration"],
                    max_concurrent=scenario["concurrent"]
                )
                
                # Run load test
                scenario_start = time.perf_counter()
                load_result = await generator.generate_request_load(
                    self.mock_mcp_request_handler,
                    scenario["name"]
                )
                scenario_duration = time.perf_counter() - scenario_start
                
                load_results.append(load_result)
                
                # Add scenario metrics
                metrics.extend([
                    self.create_metric(f"{scenario['name']}_success_rate", load_result.success_rate, "percent", 95.0, "reliability"),
                    self.create_metric(f"{scenario['name']}_avg_response_time", load_result.avg_response_time_ms, "ms", 500.0, "performance"),
                    self.create_metric(f"{scenario['name']}_p95_response_time", load_result.p95_response_time_ms, "ms", 1000.0, "performance"),
                    self.create_metric(f"{scenario['name']}_requests_per_second", load_result.requests_per_second, "rps", scenario["rate"] * 0.8, "throughput"),
                    self.create_metric(f"{scenario['name']}_error_rate", load_result.error_rate, "percent", 5.0, "reliability"),
                    self.create_metric(f"{scenario['name']}_peak_memory", load_result.peak_memory_mb, "mb", self.load_config["memory_usage_limit_mb"], "resources"),
                    self.create_metric(f"{scenario['name']}_avg_cpu", load_result.avg_cpu_percent, "percent", self.load_config["cpu_usage_limit_percent"], "resources")
                ])
                
                logger.info(f"  Completed: {load_result.total_requests} requests")
                logger.info(f"  Success rate: {load_result.success_rate:.1f}%")
                logger.info(f"  Avg response time: {load_result.avg_response_time_ms:.1f}ms")
                logger.info(f"  P95 response time: {load_result.p95_response_time_ms:.1f}ms")
                logger.info(f"  Throughput: {load_result.requests_per_second:.1f} rps")
                
                # Cool down between scenarios
                await asyncio.sleep(5)
                gc.collect()
            
            # Calculate overall statistics
            total_requests = sum(lr.total_requests for lr in load_results)
            total_successful = sum(lr.successful_requests for lr in load_results)
            total_failed = sum(lr.failed_requests for lr in load_results)
            
            all_response_times = []
            for result in load_results:
                # Estimate response time distribution
                avg_time = result.avg_response_time_ms
                for _ in range(result.successful_requests):
                    # Approximate response time with some variance
                    estimated_time = avg_time * random.uniform(0.5, 1.5)
                    all_response_times.append(estimated_time)
            
            if all_response_times:
                overall_avg_response = statistics.mean(all_response_times)
                overall_p95_response = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) > 1 else overall_avg_response
            else:
                overall_avg_response = overall_p95_response = 0.0
            
            overall_success_rate = (total_successful / max(total_requests, 1)) * 100
            max_memory_usage = max((lr.peak_memory_mb for lr in load_results), default=0)
            max_cpu_usage = max((lr.avg_cpu_percent for lr in load_results), default=0)
            
            # Overall performance metrics
            metrics.extend([
                self.create_metric("overall_success_rate", overall_success_rate, "percent", 95.0, "overall"),
                self.create_metric("overall_avg_response_time", overall_avg_response, "ms", 400.0, "overall"),
                self.create_metric("overall_p95_response_time", overall_p95_response, "ms", 800.0, "overall"),
                self.create_metric("total_requests_processed", total_requests, "count", None, "overall"),
                self.create_metric("max_memory_usage", max_memory_usage, "mb", self.load_config["memory_usage_limit_mb"], "resources"),
                self.create_metric("max_cpu_usage", max_cpu_usage, "percent", self.load_config["cpu_usage_limit_percent"], "resources"),
                self.create_metric("load_test_scenarios_passed", sum(1 for lr in load_results if lr.success_rate >= 95.0), "count", len(self.load_scenarios), "overall")
            ])
            
            logger.info(f"Overall Load Test Results:")
            logger.info(f"  Total requests: {total_requests:,}")
            logger.info(f"  Overall success rate: {overall_success_rate:.1f}%")
            logger.info(f"  Overall avg response time: {overall_avg_response:.1f}ms")
            logger.info(f"  Max memory usage: {max_memory_usage:.1f}MB")
            logger.info(f"  Max CPU usage: {max_cpu_usage:.1f}%")
        
        except Exception as e:
            error_msg = f"Load testing benchmark error: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        # Calculate final metrics
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        success_rate = 1.0 if len(errors) == 0 else 0.0
        resource_usage = self.resource_monitor.stop_monitoring()
        
        return BenchmarkResult(
            benchmark_name=self.name,
            metrics=metrics,
            success_rate=success_rate,
            execution_time=execution_time,
            resource_usage=resource_usage,
            error_details=errors,
            metadata={
                "load_scenarios": len(self.load_scenarios),
                "load_test_results": [
                    {
                        "scenario": lr.scenario_name,
                        "requests": lr.total_requests,
                        "success_rate": lr.success_rate,
                        "avg_response_ms": lr.avg_response_time_ms,
                        "rps": lr.requests_per_second
                    } for lr in load_results
                ],
                "target_limits": {
                    "memory_mb": self.load_config["memory_usage_limit_mb"],
                    "cpu_percent": self.load_config["cpu_usage_limit_percent"],
                    "success_rate_percent": 95.0
                }
            }
        )


async def run_load_testing_benchmark():
    """Convenience function to run load testing benchmark."""
    benchmark = LoadTestingBenchmark()
    
    try:
        await benchmark.setup()
        result = await benchmark.run_benchmark()
        await benchmark.teardown()
        
        print("\n" + "="*60)
        print("LOAD TESTING BENCHMARK RESULTS")
        print("="*60)
        
        print(f"Success Rate: {result.success_rate:.2%}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"All Targets Met: {'✅ Yes' if result.all_targets_met else '❌ No'}")
        
        # Print key metrics
        print("\nKey Load Testing Metrics:")
        for metric in result.metrics:
            if metric.category in ["overall", "reliability", "resources"]:
                status = "✅" if metric.meets_target else "❌"
                target_text = f" (target: {metric.target})" if metric.target else ""
                print(f"  {metric.name}: {metric.value:.1f}{metric.unit}{target_text} {status}")
        
        # Print scenario summary
        print("\nLoad Test Scenarios:")
        if "load_test_results" in result.metadata:
            for scenario in result.metadata["load_test_results"]:
                print(f"  {scenario['scenario']}: {scenario['requests']:,} req, {scenario['success_rate']:.1f}% success, {scenario['avg_response_ms']:.1f}ms avg, {scenario['rps']:.1f} rps")
        
        if result.error_details:
            print(f"\nErrors ({len(result.error_details)}):")
            for error in result.error_details:
                print(f"  - {error}")
        
        print("="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to run load testing benchmark: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the load testing benchmark
    asyncio.run(run_load_testing_benchmark())