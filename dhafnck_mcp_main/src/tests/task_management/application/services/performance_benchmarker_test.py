"""
Tests for Performance Benchmarker Service
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any, Callable

from fastmcp.task_management.application.services.performance_benchmarker import (
    PerformanceBenchmarker,
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkCategory
)


class TestPerformanceBenchmarker:
    """Test Performance Benchmarker functionality"""

    @pytest.fixture
    def benchmarker(self):
        """Create performance benchmarker instance"""
        return PerformanceBenchmarker()

    @pytest.fixture
    def sample_benchmark_func(self):
        """Sample function to benchmark"""
        def compute_intensive_task(n: int) -> int:
            """Simulated compute-intensive task"""
            result = 0
            for i in range(n):
                result += i ** 2
            return result
        return compute_intensive_task

    @pytest.fixture
    async def sample_async_func(self):
        """Sample async function to benchmark"""
        async def async_io_task(delay: float) -> str:
            """Simulated I/O-bound async task"""
            await asyncio.sleep(delay)
            return f"Completed after {delay}s"
        return async_io_task

    def test_benchmarker_initialization(self):
        """Test benchmarker initialization"""
        benchmarker = PerformanceBenchmarker(
            warmup_runs=5,
            benchmark_runs=100
        )
        assert benchmarker.warmup_runs == 5
        assert benchmarker.benchmark_runs == 100
        assert benchmarker.results == []

    def test_simple_benchmark(self, benchmarker, sample_benchmark_func):
        """Test simple function benchmarking"""
        result = benchmarker.benchmark(
            func=sample_benchmark_func,
            args=(1000,),
            name="compute_intensive_1000"
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.name == "compute_intensive_1000"
        assert result.mean_time > 0
        assert result.min_time > 0
        assert result.max_time >= result.min_time
        assert result.std_dev >= 0
        assert len(result.all_times) == benchmarker.benchmark_runs

    @pytest.mark.asyncio
    async def test_async_benchmark(self, benchmarker, sample_async_func):
        """Test async function benchmarking"""
        result = await benchmarker.benchmark_async(
            func=sample_async_func,
            args=(0.01,),  # 10ms delay
            name="async_io_task"
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.name == "async_io_task"
        assert result.mean_time >= 0.01  # At least the delay time
        assert result.is_async is True

    def test_benchmark_with_setup_teardown(self, benchmarker):
        """Test benchmarking with setup and teardown"""
        setup_called = []
        teardown_called = []
        
        def setup():
            setup_called.append(True)
            return {"data": list(range(1000))}
        
        def teardown(context):
            teardown_called.append(True)
        
        def process_data(context):
            return sum(context["data"])
        
        result = benchmarker.benchmark(
            func=process_data,
            name="process_with_setup",
            setup=setup,
            teardown=teardown
        )
        
        assert len(setup_called) == benchmarker.benchmark_runs + benchmarker.warmup_runs
        assert len(teardown_called) == benchmarker.benchmark_runs + benchmarker.warmup_runs
        assert result.mean_time > 0

    def test_benchmark_suite(self, benchmarker):
        """Test running a benchmark suite"""
        suite = BenchmarkSuite(
            name="Math Operations",
            description="Benchmark various math operations"
        )
        
        # Add benchmarks to suite
        suite.add_benchmark(
            name="addition",
            func=lambda: sum(range(1000))
        )
        suite.add_benchmark(
            name="multiplication",
            func=lambda: eval("*".join(map(str, range(1, 10))))
        )
        suite.add_benchmark(
            name="power",
            func=lambda: [x**2 for x in range(100)]
        )
        
        # Run suite
        results = benchmarker.run_suite(suite)
        
        assert len(results) == 3
        assert all(isinstance(r, BenchmarkResult) for r in results)
        assert any(r.name == "addition" for r in results)

    def test_memory_benchmarking(self, benchmarker):
        """Test memory usage benchmarking"""
        def memory_intensive_task():
            # Create large list
            data = [i for i in range(1000000)]
            # Process data
            return sum(data)
        
        result = benchmarker.benchmark_memory(
            func=memory_intensive_task,
            name="memory_intensive"
        )
        
        assert result.peak_memory > 0
        assert result.memory_delta >= 0
        assert "memory_profile" in result.metadata

    def test_performance_targets(self, benchmarker):
        """Test performance target validation"""
        target = PerformanceTarget(
            name="api_response",
            max_time=0.1,  # 100ms
            max_memory=10 * 1024 * 1024,  # 10MB
            percentile_targets={
                95: 0.08,  # 95th percentile < 80ms
                99: 0.095  # 99th percentile < 95ms
            }
        )
        
        def fast_function():
            time.sleep(0.001)  # 1ms
            return "done"
        
        result = benchmarker.benchmark(
            func=fast_function,
            name="fast_api_call"
        )
        
        # Check against target
        passed = benchmarker.check_target(result, target)
        assert passed is True

    def test_benchmark_comparison(self, benchmarker):
        """Test comparing benchmark results"""
        # Benchmark two implementations
        def implementation_v1(n):
            return sum(range(n))
        
        def implementation_v2(n):
            return n * (n - 1) // 2  # Mathematical formula
        
        result_v1 = benchmarker.benchmark(
            func=implementation_v1,
            args=(10000,),
            name="sum_v1"
        )
        
        result_v2 = benchmarker.benchmark(
            func=implementation_v2,
            args=(10000,),
            name="sum_v2"
        )
        
        # Compare results
        comparison = benchmarker.compare(result_v1, result_v2)
        
        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.speedup > 1  # v2 should be faster
        assert comparison.winner == "sum_v2"
        assert comparison.statistical_significance is not None

    def test_profile_generation(self, benchmarker):
        """Test performance profile generation"""
        def complex_function(n):
            # Multiple operations to profile
            data = list(range(n))
            sorted_data = sorted(data, reverse=True)
            filtered = [x for x in sorted_data if x % 2 == 0]
            return sum(filtered)
        
        profile = benchmarker.profile(
            func=complex_function,
            args=(1000,),
            profile_type="line"
        )
        
        assert "function_calls" in profile
        assert "time_per_line" in profile
        assert "hotspots" in profile
        assert len(profile["hotspots"]) > 0

    def test_regression_detection(self, benchmarker):
        """Test performance regression detection"""
        # Simulate historical results
        historical = [
            BenchmarkResult(
                name="api_endpoint",
                mean_time=0.05,
                min_time=0.045,
                max_time=0.055,
                std_dev=0.002,
                all_times=[0.05] * 100
            )
        ]
        
        # Current result with regression
        current = BenchmarkResult(
            name="api_endpoint",
            mean_time=0.08,  # 60% slower
            min_time=0.075,
            max_time=0.085,
            std_dev=0.002,
            all_times=[0.08] * 100
        )
        
        regression = benchmarker.detect_regression(
            current=current,
            historical=historical,
            threshold=0.1  # 10% regression threshold
        )
        
        assert regression is True
        assert benchmarker.calculate_regression_severity(current, historical) > 0.5

    def test_benchmark_export(self, benchmarker, sample_benchmark_func):
        """Test exporting benchmark results"""
        # Run multiple benchmarks
        for i in [100, 500, 1000]:
            benchmarker.benchmark(
                func=sample_benchmark_func,
                args=(i,),
                name=f"compute_{i}"
            )
        
        # Export results
        csv_export = benchmarker.export_results(format="csv")
        assert "name,mean_time,min_time,max_time" in csv_export
        assert "compute_100" in csv_export
        
        json_export = benchmarker.export_results(format="json")
        import json
        data = json.loads(json_export)
        assert len(data) == 3

    def test_concurrent_benchmarking(self, benchmarker):
        """Test benchmarking concurrent operations"""
        import concurrent.futures
        
        def parallel_task(n):
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(sum, range(n//4)) for _ in range(4)]
                results = [f.result() for f in futures]
                return sum(results)
        
        result = benchmarker.benchmark(
            func=parallel_task,
            args=(10000,),
            name="parallel_computation"
        )
        
        assert result.metadata.get("parallelism") is not None
        assert result.mean_time > 0

    def test_benchmark_context_manager(self, benchmarker):
        """Test benchmark context manager for inline benchmarking"""
        with benchmarker.measure("inline_operation") as ctx:
            # Simulate some work
            total = sum(range(1000))
            time.sleep(0.01)
        
        assert ctx.elapsed_time > 0.01
        assert ctx.result_stored is True
        
        # Result should be stored
        results = benchmarker.get_results("inline_operation")
        assert len(results) > 0

    def test_statistical_analysis(self, benchmarker):
        """Test statistical analysis of benchmark results"""
        # Create result with known distribution
        times = [0.1 + (i % 10) * 0.001 for i in range(100)]
        result = BenchmarkResult(
            name="test",
            mean_time=sum(times) / len(times),
            min_time=min(times),
            max_time=max(times),
            std_dev=0,  # Will be calculated
            all_times=times
        )
        
        stats = benchmarker.analyze_statistics(result)
        
        assert "percentiles" in stats
        assert stats["percentiles"][50] > 0  # Median
        assert stats["percentiles"][95] > stats["percentiles"][50]
        assert "outliers" in stats
        assert "confidence_interval" in stats

    def test_benchmark_caching(self, benchmarker):
        """Test caching of benchmark results"""
        def expensive_func():
            time.sleep(0.1)
            return "result"
        
        # First run
        result1 = benchmarker.benchmark(
            func=expensive_func,
            name="cached_bench",
            cache_key="test_v1"
        )
        
        # Second run with same cache key should be faster
        start = time.time()
        result2 = benchmarker.benchmark(
            func=expensive_func,
            name="cached_bench",
            cache_key="test_v1",
            use_cache=True
        )
        elapsed = time.time() - start
        
        assert elapsed < 0.05  # Should not re-run the expensive function
        assert result2.cached is True

    def test_adaptive_benchmarking(self, benchmarker):
        """Test adaptive benchmark runs based on variance"""
        def variable_func():
            # Function with high variance
            import random
            delay = random.uniform(0.001, 0.01)
            time.sleep(delay)
            return delay
        
        result = benchmarker.benchmark_adaptive(
            func=variable_func,
            name="variable_timing",
            min_runs=10,
            max_runs=1000,
            confidence_level=0.95
        )
        
        # Should run more iterations for high variance function
        assert len(result.all_times) > 10
        assert result.confidence_interval is not None

    def test_benchmark_report_generation(self, benchmarker, sample_benchmark_func):
        """Test comprehensive benchmark report generation"""
        # Run various benchmarks
        for i in [100, 500, 1000, 5000]:
            benchmarker.benchmark(
                func=sample_benchmark_func,
                args=(i,),
                name=f"compute_{i}"
            )
        
        # Generate report
        report = benchmarker.generate_report(
            include_charts=True,
            include_recommendations=True
        )
        
        assert "summary" in report
        assert "detailed_results" in report
        assert "charts" in report
        assert "recommendations" in report
        assert len(report["recommendations"]) > 0