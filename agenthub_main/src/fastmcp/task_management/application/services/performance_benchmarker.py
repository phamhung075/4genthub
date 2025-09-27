"""Performance Benchmarker for MCP Response Optimization

This module provides comprehensive performance benchmarking and measurement
for the MCP response optimization system.
"""

import logging
import time
import statistics
import json
import sys
import asyncio
import csv
import io
import random
import tracemalloc
import concurrent.futures

# Try to import psutil, but don't fail if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class BenchmarkCategory(Enum):
    """Benchmark categories"""
    RESPONSE_OPTIMIZATION = "response_optimization"
    CONTEXT_SELECTION = "context_selection" 
    TEMPLATE_PROCESSING = "template_processing"
    CACHE_PERFORMANCE = "cache_performance"
    END_TO_END = "end_to_end"


@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    name: str
    mean_time: float
    min_time: float
    max_time: float
    std_dev: float
    all_times: List[float] = field(default_factory=list)
    category: Optional[BenchmarkCategory] = None
    execution_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    success: Optional[bool] = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_async: bool = False
    cached: bool = False
    peak_memory: Optional[float] = None
    memory_delta: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio"""
        if self.input_size_bytes == 0:
            return 0.0
        return (1 - self.output_size_bytes / self.input_size_bytes) * 100
    
    @property
    def throughput_mb_per_sec(self) -> float:
        """Calculate throughput in MB/sec"""
        if self.execution_time_ms == 0:
            return 0.0
        return (self.input_size_bytes / (1024 * 1024)) / (self.execution_time_ms / 1000)


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results"""
    name: str = ""
    description: str = ""
    suite_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: List[BenchmarkResult] = field(default_factory=list)
    benchmarks: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        if self.suite_name and not self.name:
            self.name = self.suite_name
        if self.name and not self.suite_name:
            self.suite_name = self.name

    def add_result(self, result: BenchmarkResult) -> None:
        """Add benchmark result"""
        self.results.append(result)

    def add_benchmark(
        self,
        name: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict] = None
    ) -> None:
        """Add a benchmark to the suite"""
        self.benchmarks.append({
            'name': name,
            'func': func,
            'args': args,
            'kwargs': kwargs or {}
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.results:
            return {"error": "No results available"}
        
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return {"error": "No successful results"}
        
        execution_times = [r.execution_time_ms for r in successful_results]
        compression_ratios = [r.compression_ratio for r in successful_results]
        throughputs = [r.throughput_mb_per_sec for r in successful_results]
        
        return {
            "total_benchmarks": len(self.results),
            "successful_benchmarks": len(successful_results),
            "success_rate_percent": (len(successful_results) / len(self.results)) * 100,
            "performance": {
                "avg_execution_time_ms": statistics.mean(execution_times),
                "median_execution_time_ms": statistics.median(execution_times),
                "p95_execution_time_ms": statistics.quantiles(execution_times, n=20)[18] if len(execution_times) >= 20 else max(execution_times),
                "min_execution_time_ms": min(execution_times),
                "max_execution_time_ms": max(execution_times)
            },
            "compression": {
                "avg_compression_ratio_percent": statistics.mean(compression_ratios),
                "median_compression_ratio_percent": statistics.median(compression_ratios),
                "min_compression_ratio_percent": min(compression_ratios),
                "max_compression_ratio_percent": max(compression_ratios)
            },
            "throughput": {
                "avg_throughput_mb_per_sec": statistics.mean(throughputs),
                "median_throughput_mb_per_sec": statistics.median(throughputs),
                "max_throughput_mb_per_sec": max(throughputs)
            }
        }


@dataclass
class PerformanceTarget:
    """Performance target configuration"""
    name: str
    max_time: float
    max_memory: Optional[float] = None
    percentile_targets: Dict[int, float] = field(default_factory=dict)


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark results"""
    speedup: float
    winner: str
    statistical_significance: Optional[float] = None


class PerformanceBenchmarker:
    """Comprehensive performance benchmarker"""

    def __init__(self, warmup_runs: int = 3, benchmark_runs: int = 10):
        """Initialize benchmarker"""
        self.warmup_runs = warmup_runs
        self.benchmark_runs = benchmark_runs
        self.results: List[BenchmarkResult] = []
        self.current_suite: Optional[BenchmarkSuite] = None
        self.completed_suites: List[BenchmarkSuite] = []
        self._cache: Dict[str, BenchmarkResult] = {}
        
    def start_suite(self, name: str) -> BenchmarkSuite:
        """Start a new benchmark suite"""
        self.current_suite = BenchmarkSuite(
            suite_name=name,
            started_at=datetime.now()
        )
        return self.current_suite
    
    def complete_suite(self) -> Optional[BenchmarkSuite]:
        """Complete current benchmark suite"""
        if self.current_suite:
            self.current_suite.completed_at = datetime.now()
            self.completed_suites.append(self.current_suite)
            completed = self.current_suite
            self.current_suite = None
            return completed
        return None
    
    @contextmanager
    def benchmark(
        self,
        name: str,
        category: BenchmarkCategory,
        input_data: Any = None
    ):
        """Context manager for benchmarking operations"""
        # Measure memory before
        try:
            import tracemalloc
            tracemalloc.start()
            memory_before = tracemalloc.get_traced_memory()[0]
        except:
            memory_before = 0
        
        # Calculate input size
        input_size = 0
        if input_data:
            try:
                input_size = len(json.dumps(input_data, default=str).encode('utf-8'))
            except:
                input_size = sys.getsizeof(input_data)
        
        # Start timing
        start_time = time.perf_counter()
        
        result = BenchmarkResult(
            name=name,
            category=category,
            execution_time_ms=0,
            memory_usage_mb=0,
            input_size_bytes=input_size,
            output_size_bytes=0,
            success=False
        )
        
        try:
            yield result
            result.success = True
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Benchmark {name} failed: {e}")
        finally:
            # Calculate execution time
            end_time = time.perf_counter()
            result.execution_time_ms = (end_time - start_time) * 1000
            
            # Measure memory after
            try:
                memory_after = tracemalloc.get_traced_memory()[0]
                result.memory_usage_mb = (memory_after - memory_before) / (1024 * 1024)
                tracemalloc.stop()
            except:
                result.memory_usage_mb = 0
            
            # Add to current suite
            if self.current_suite:
                self.current_suite.add_result(result)
    
    def benchmark_response_optimization(
        self,
        optimizer: Any,
        test_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark response optimization performance"""
        results = {}
        
        # Test different response sizes
        for i, response in enumerate(test_responses):
            with self.benchmark(
                f"response_optimization_test_{i+1}",
                BenchmarkCategory.RESPONSE_OPTIMIZATION,
                response
            ) as benchmark:
                
                # Run optimization
                optimized = optimizer.optimize_response(response.copy())
                
                # Calculate output size
                try:
                    benchmark.output_size_bytes = len(json.dumps(optimized, default=str).encode('utf-8'))
                except:
                    benchmark.output_size_bytes = sys.getsizeof(optimized)
                
                benchmark.metadata = {
                    "original_fields": len(response),
                    "optimized_fields": len(optimized),
                    "profile_used": getattr(optimized, '_profile_used', 'unknown')
                }
        
        return self._get_category_summary(BenchmarkCategory.RESPONSE_OPTIMIZATION)
    
    def benchmark_context_selection(
        self,
        field_selector: Any,
        template_manager: Any,
        test_contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark context field selection performance"""
        from fastmcp.task_management.application.services.context_field_selector import FieldSet
        from fastmcp.task_management.application.services.context_template_manager import OperationType
        
        # Test different field sets
        field_sets = [FieldSet.MINIMAL, FieldSet.SUMMARY, FieldSet.DETAIL]
        operations = [OperationType.TASK_GET, OperationType.TASK_LIST, OperationType.TASK_UPDATE]
        
        for context in test_contexts:
            for field_set in field_sets:
                for operation in operations:
                    test_name = f"context_selection_{field_set.value}_{operation.value}"
                    
                    with self.benchmark(
                        test_name,
                        BenchmarkCategory.CONTEXT_SELECTION,
                        context
                    ) as benchmark:
                        
                        # Get template
                        template = template_manager.get_template(operation)
                        
                        # Get minimal context
                        minimal = template_manager.get_minimal_context(operation, context)
                        
                        # Calculate savings
                        try:
                            benchmark.output_size_bytes = len(json.dumps(minimal, default=str).encode('utf-8'))
                        except:
                            benchmark.output_size_bytes = sys.getsizeof(minimal)
                        
                        benchmark.metadata = {
                            "field_set": field_set.value,
                            "operation": operation.value,
                            "template_fields": len(template),
                            "context_types": list(context.keys())
                        }
        
        return self._get_category_summary(BenchmarkCategory.CONTEXT_SELECTION)
    
    def benchmark_cache_performance(
        self,
        cache_optimizer: Any,
        test_data: List[Tuple[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark cache performance"""
        
        # Warm up cache
        with self.benchmark(
            "cache_warmup",
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            warmed = 0
            for key, data in test_data[:10]:  # Warm with first 10 items
                if cache_optimizer.put(key, data, "benchmark"):
                    warmed += 1
            
            benchmark.metadata = {"entries_warmed": warmed}
            benchmark.output_size_bytes = warmed
        
        # Test cache hits
        with self.benchmark(
            "cache_hit_performance",
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            hits = 0
            for key, _ in test_data[:10]:
                if cache_optimizer.get(key, "benchmark"):
                    hits += 1
            
            benchmark.metadata = {"cache_hits": hits}
            benchmark.output_size_bytes = hits
        
        # Test cache misses
        with self.benchmark(
            "cache_miss_performance", 
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            misses = 0
            for i in range(100, 110):  # Keys that don't exist
                if cache_optimizer.get(f"nonexistent_{i}", "benchmark") is None:
                    misses += 1
            
            benchmark.metadata = {"cache_misses": misses}
        
        # Test cache optimization
        with self.benchmark(
            "cache_optimization",
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            optimization_result = cache_optimizer.optimize_cache()
            benchmark.metadata = optimization_result
        
        return self._get_category_summary(BenchmarkCategory.CACHE_PERFORMANCE)
    
    def benchmark_end_to_end(
        self,
        optimizer: Any,
        template_manager: Any,
        test_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark complete end-to-end optimization pipeline"""
        
        for i, scenario in enumerate(test_scenarios):
            with self.benchmark(
                f"end_to_end_scenario_{i+1}",
                BenchmarkCategory.END_TO_END,
                scenario
            ) as benchmark:
                
                # Step 1: Get template for operation
                operation = scenario.get('operation', 'task.get')
                try:
                    from fastmcp.task_management.application.services.context_template_manager import OperationType
                    op_enum = OperationType(operation)
                    template = template_manager.get_template(op_enum)
                except:
                    template = {}
                
                # Step 2: Extract minimal context
                context_data = scenario.get('context', {})
                if template and context_data:
                    minimal_context = template_manager.get_minimal_context(op_enum, context_data)
                else:
                    minimal_context = context_data
                
                # Step 3: Create response
                response = {
                    "status": "success",
                    "operation": operation,
                    "data": scenario.get('data', {}),
                    "context": minimal_context,
                    "metadata": scenario.get('metadata', {}),
                    "workflow_guidance": scenario.get('workflow_guidance', {})
                }
                
                # Step 4: Optimize response
                optimized = optimizer.optimize_response(response.copy())
                
                # Calculate metrics
                try:
                    benchmark.output_size_bytes = len(json.dumps(optimized, default=str).encode('utf-8'))
                    original_size = len(json.dumps(response, default=str).encode('utf-8'))
                    
                    benchmark.metadata = {
                        "operation": operation,
                        "original_response_size": original_size,
                        "optimized_response_size": benchmark.output_size_bytes,
                        "compression_achieved": (1 - benchmark.output_size_bytes / original_size) * 100,
                        "context_types_processed": len(minimal_context),
                        "template_fields": len(template)
                    }
                except:
                    benchmark.output_size_bytes = sys.getsizeof(optimized)
        
        return self._get_category_summary(BenchmarkCategory.END_TO_END)
    
    def _get_category_summary(self, category: BenchmarkCategory) -> Dict[str, Any]:
        """Get summary for specific category"""
        if not self.current_suite:
            return {"error": "No active benchmark suite"}
        
        category_results = [
            r for r in self.current_suite.results 
            if r.category == category
        ]
        
        if not category_results:
            return {"error": f"No results for category {category.value}"}
        
        successful = [r for r in category_results if r.success]
        
        if not successful:
            return {"error": f"No successful results for category {category.value}"}
        
        execution_times = [r.execution_time_ms for r in successful]
        compression_ratios = [r.compression_ratio for r in successful if r.input_size_bytes > 0]
        
        summary = {
            "category": category.value,
            "total_tests": len(category_results),
            "successful_tests": len(successful),
            "success_rate_percent": (len(successful) / len(category_results)) * 100,
            "avg_execution_time_ms": statistics.mean(execution_times),
            "median_execution_time_ms": statistics.median(execution_times),
            "total_execution_time_ms": sum(execution_times)
        }
        
        if compression_ratios:
            summary.update({
                "avg_compression_ratio_percent": statistics.mean(compression_ratios),
                "median_compression_ratio_percent": statistics.median(compression_ratios),
                "max_compression_ratio_percent": max(compression_ratios)
            })
        
        return summary
    
    def generate_report(
        self,
        suite: Optional[BenchmarkSuite] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        target_suite = suite or self.current_suite
        
        if not target_suite:
            return {"error": "No benchmark suite available"}
        
        report = {
            "suite_name": target_suite.suite_name,
            "started_at": target_suite.started_at.isoformat(),
            "completed_at": target_suite.completed_at.isoformat() if target_suite.completed_at else None,
            "summary": target_suite.get_summary(),
            "category_summaries": {},
            "performance_comparison": self._compare_with_baseline(),
            "recommendations": self._generate_recommendations(target_suite)
        }
        
        # Add category summaries
        categories = set(r.category for r in target_suite.results)
        for category in categories:
            report["category_summaries"][category.value] = self._get_category_summary(category)
        
        return report
    
    def _compare_with_baseline(self) -> Dict[str, Any]:
        """Compare current results with baseline performance"""
        # Define baseline metrics (before optimization)
        baseline = {
            "response_processing_ms": 100,  # 100ms baseline
            "response_size_bytes": 5000,    # 5KB baseline
            "compression_ratio_percent": 0,  # No compression baseline
            "cache_hit_rate_percent": 0      # No cache baseline
        }
        
        if not self.current_suite or not self.current_suite.results:
            return {"error": "No current results to compare"}
        
        successful_results = [r for r in self.current_suite.results if r.success]
        
        if not successful_results:
            return {"error": "No successful results to compare"}
        
        # Calculate current metrics
        avg_execution_time = statistics.mean([r.execution_time_ms for r in successful_results])
        avg_output_size = statistics.mean([r.output_size_bytes for r in successful_results])
        compression_ratios = [r.compression_ratio for r in successful_results if r.input_size_bytes > 0]
        avg_compression = statistics.mean(compression_ratios) if compression_ratios else 0
        
        # Calculate improvements
        return {
            "baseline_metrics": baseline,
            "current_metrics": {
                "avg_execution_time_ms": avg_execution_time,
                "avg_output_size_bytes": avg_output_size,
                "avg_compression_ratio_percent": avg_compression
            },
            "improvements": {
                "execution_time_improvement_percent": max(0, (baseline["response_processing_ms"] - avg_execution_time) / baseline["response_processing_ms"] * 100),
                "size_reduction_percent": max(0, (baseline["response_size_bytes"] - avg_output_size) / baseline["response_size_bytes"] * 100),
                "compression_achievement_percent": avg_compression
            }
        }
    
    def _generate_recommendations(
        self,
        suite: BenchmarkSuite
    ) -> List[str]:
        """Generate optimization recommendations based on results"""
        recommendations = []
        
        successful_results = [r for r in suite.results if r.success]
        
        if not successful_results:
            return ["No successful benchmarks to analyze"]
        
        # Analyze execution times
        execution_times = [r.execution_time_ms for r in successful_results]
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        
        if avg_time > 50:
            recommendations.append("Consider optimizing response processing - average time exceeds 50ms")
        
        if max_time > 200:
            recommendations.append("Some operations are very slow (>200ms) - investigate bottlenecks")
        
        # Analyze compression ratios
        compression_ratios = [r.compression_ratio for r in successful_results if r.input_size_bytes > 0]
        if compression_ratios:
            avg_compression = statistics.mean(compression_ratios)
            
            if avg_compression < 50:
                recommendations.append("Compression ratio below 50% - review optimization strategies")
            elif avg_compression > 80:
                recommendations.append("Excellent compression ratio achieved - current optimization is effective")
        
        # Analyze memory usage
        memory_usage = [r.memory_usage_mb for r in successful_results if r.memory_usage_mb > 0]
        if memory_usage:
            avg_memory = statistics.mean(memory_usage)
            if avg_memory > 10:
                recommendations.append("High memory usage detected - consider memory optimization")
        
        # Category-specific recommendations
        categories = set(r.category for r in successful_results)
        
        if BenchmarkCategory.CACHE_PERFORMANCE in categories:
            cache_results = [r for r in successful_results if r.category == BenchmarkCategory.CACHE_PERFORMANCE]
            cache_times = [r.execution_time_ms for r in cache_results]
            avg_cache_time = statistics.mean(cache_times)
            
            if avg_cache_time > 10:
                recommendations.append("Cache operations are slow - consider cache optimization")
        
        return recommendations if recommendations else ["Performance looks good - no specific recommendations"]

    def benchmark(
        self,
        func: Optional[Callable] = None,
        args: Tuple = (),
        kwargs: Optional[Dict] = None,
        name: Optional[str] = None,
        setup: Optional[Callable] = None,
        teardown: Optional[Callable] = None,
        cache_key: Optional[str] = None,
        use_cache: bool = False,
        profile_type: Optional[str] = None
    ) -> BenchmarkResult:
        """Benchmark a function with warmup and multiple runs"""
        if kwargs is None:
            kwargs = {}

        # Check cache
        if use_cache and cache_key and cache_key in self._cache:
            cached_result = self._cache[cache_key]
            cached_result.cached = True
            return cached_result

        all_times = []

        # Warmup runs
        for _ in range(self.warmup_runs):
            context = {}
            if setup:
                context = setup()

            start = time.perf_counter()
            if context:
                func(context)
            else:
                func(*args, **kwargs)
            end = time.perf_counter()

            if teardown:
                teardown(context)

        # Actual benchmark runs
        for _ in range(self.benchmark_runs):
            context = {}
            if setup:
                context = setup()

            start = time.perf_counter()
            if context:
                func(context)
            else:
                func(*args, **kwargs)
            end = time.perf_counter()

            all_times.append(end - start)

            if teardown:
                teardown(context)

        # Calculate statistics
        result = BenchmarkResult(
            name=name or func.__name__,
            mean_time=statistics.mean(all_times),
            min_time=min(all_times),
            max_time=max(all_times),
            std_dev=statistics.stdev(all_times) if len(all_times) > 1 else 0,
            all_times=all_times
        )

        # Store in results and cache
        self.results.append(result)
        if cache_key:
            self._cache[cache_key] = result

        return result

    async def benchmark_async(
        self,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict] = None,
        name: Optional[str] = None
    ) -> BenchmarkResult:
        """Benchmark an async function"""
        if kwargs is None:
            kwargs = {}

        all_times = []

        # Warmup runs
        for _ in range(self.warmup_runs):
            start = time.perf_counter()
            await func(*args, **kwargs)
            end = time.perf_counter()

        # Actual benchmark runs
        for _ in range(self.benchmark_runs):
            start = time.perf_counter()
            await func(*args, **kwargs)
            end = time.perf_counter()
            all_times.append(end - start)

        # Calculate statistics
        result = BenchmarkResult(
            name=name or func.__name__,
            mean_time=statistics.mean(all_times),
            min_time=min(all_times),
            max_time=max(all_times),
            std_dev=statistics.stdev(all_times) if len(all_times) > 1 else 0,
            all_times=all_times,
            is_async=True
        )

        self.results.append(result)
        return result

    def run_suite(self, suite: BenchmarkSuite) -> List[BenchmarkResult]:
        """Run a benchmark suite"""
        results = []
        for benchmark_info in suite.benchmarks:
            result = self.benchmark(
                func=benchmark_info['func'],
                name=benchmark_info['name'],
                args=benchmark_info.get('args', ()),
                kwargs=benchmark_info.get('kwargs', {})
            )
            results.append(result)
        return results

    def benchmark_memory(
        self,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict] = None,
        name: Optional[str] = None
    ) -> BenchmarkResult:
        """Benchmark memory usage of a function"""
        if kwargs is None:
            kwargs = {}

        # Start memory tracking
        tracemalloc.start()
        memory_before = tracemalloc.get_traced_memory()[0]

        # Get process memory if psutil is available
        mem_info_before = None
        mem_info_after = None
        if HAS_PSUTIL:
            process = psutil.Process()
            mem_info_before = process.memory_info()

        # Run function
        start = time.perf_counter()
        result_value = func(*args, **kwargs)
        end = time.perf_counter()

        # Get memory after
        memory_after = tracemalloc.get_traced_memory()[0]
        if HAS_PSUTIL:
            mem_info_after = process.memory_info()
        peak_memory = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        memory_delta = memory_after - memory_before

        metadata = {
            "memory_profile": {
                "before_bytes": memory_before,
                "after_bytes": memory_after,
                "peak_bytes": peak_memory,
                "delta_bytes": memory_delta
            }
        }

        if mem_info_before and mem_info_after:
            metadata["memory_profile"]["rss_before"] = mem_info_before.rss
            metadata["memory_profile"]["rss_after"] = mem_info_after.rss

        result = BenchmarkResult(
            name=name or func.__name__,
            mean_time=end - start,
            min_time=end - start,
            max_time=end - start,
            std_dev=0,
            all_times=[end - start],
            peak_memory=peak_memory / (1024 * 1024),  # Convert to MB
            memory_delta=memory_delta / (1024 * 1024),  # Convert to MB
            metadata=metadata
        )

        self.results.append(result)
        return result

    def check_target(
        self,
        result: BenchmarkResult,
        target: PerformanceTarget
    ) -> bool:
        """Check if a benchmark result meets performance targets"""
        # Check max time
        if result.mean_time > target.max_time:
            return False

        # Check max memory if specified
        if target.max_memory and result.peak_memory:
            if result.peak_memory > target.max_memory / (1024 * 1024):  # Convert to MB
                return False

        # Check percentile targets
        if target.percentile_targets and result.all_times:
            for percentile, max_time in target.percentile_targets.items():
                percentile_value = statistics.quantiles(
                    result.all_times,
                    n=100
                )[percentile - 1] if len(result.all_times) >= 100 else max(result.all_times)

                if percentile_value > max_time:
                    return False

        return True

    def compare(
        self,
        result1: BenchmarkResult,
        result2: BenchmarkResult
    ) -> BenchmarkComparison:
        """Compare two benchmark results"""
        speedup = result1.mean_time / result2.mean_time if result2.mean_time > 0 else float('inf')
        winner = result2.name if speedup > 1 else result1.name

        # Calculate statistical significance using t-test approximation
        significance = None
        if result1.all_times and result2.all_times:
            # Simple significance check based on standard deviations
            combined_std = (result1.std_dev + result2.std_dev) / 2
            if combined_std > 0:
                difference = abs(result1.mean_time - result2.mean_time)
                significance = difference / combined_std

        return BenchmarkComparison(
            speedup=speedup,
            winner=winner,
            statistical_significance=significance
        )

    def profile(
        self,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict] = None,
        profile_type: str = "line"
    ) -> Dict[str, Any]:
        """Profile a function execution"""
        if kwargs is None:
            kwargs = {}

        import cProfile
        import pstats
        from io import StringIO

        profiler = cProfile.Profile()
        profiler.enable()
        func(*args, **kwargs)
        profiler.disable()

        # Get stats
        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')

        # Extract profile data
        profile_data = {
            "function_calls": {},
            "time_per_line": {},
            "hotspots": []
        }

        # Get top functions by time
        stats.sort_stats('time')
        for func_info, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:10]:
            func_name = f"{func_info[0]}:{func_info[1]}:{func_info[2]}"
            profile_data["function_calls"][func_name] = {
                "calls": nc,
                "total_time": tt,
                "cumulative_time": ct
            }
            profile_data["hotspots"].append(func_name)

        return profile_data

    def detect_regression(
        self,
        current: BenchmarkResult,
        historical: List[BenchmarkResult],
        threshold: float = 0.1
    ) -> bool:
        """Detect performance regression"""
        if not historical:
            return False

        # Calculate historical average
        historical_mean = statistics.mean([r.mean_time for r in historical])

        # Check if current is slower by more than threshold
        if current.mean_time > historical_mean * (1 + threshold):
            return True

        return False

    def calculate_regression_severity(
        self,
        current: BenchmarkResult,
        historical: List[BenchmarkResult]
    ) -> float:
        """Calculate severity of regression (0-1 scale)"""
        if not historical:
            return 0.0

        historical_mean = statistics.mean([r.mean_time for r in historical])
        if historical_mean == 0:
            return 0.0

        # Calculate percentage slower
        percent_slower = (current.mean_time - historical_mean) / historical_mean

        # Cap at 1.0 for 100% or more slower
        return min(1.0, max(0.0, percent_slower))

    def export_results(self, format: str = "json") -> str:
        """Export benchmark results"""
        if format == "json":
            data = []
            for result in self.results:
                data.append({
                    "name": result.name,
                    "mean_time": result.mean_time,
                    "min_time": result.min_time,
                    "max_time": result.max_time,
                    "std_dev": result.std_dev,
                    "is_async": result.is_async,
                    "cached": result.cached
                })
            return json.dumps(data, indent=2)

        elif format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["name", "mean_time", "min_time", "max_time", "std_dev"])

            for result in self.results:
                writer.writerow([
                    result.name,
                    result.mean_time,
                    result.min_time,
                    result.max_time,
                    result.std_dev
                ])

            return output.getvalue()

        return ""

    @contextmanager
    def measure(self, name: str):
        """Context manager for inline benchmarking"""
        start = time.perf_counter()
        context = type('Context', (), {
            'elapsed_time': 0,
            'result_stored': False
        })()

        try:
            yield context
        finally:
            end = time.perf_counter()
            context.elapsed_time = end - start

            # Store result
            result = BenchmarkResult(
                name=name,
                mean_time=context.elapsed_time,
                min_time=context.elapsed_time,
                max_time=context.elapsed_time,
                std_dev=0,
                all_times=[context.elapsed_time]
            )
            self.results.append(result)
            context.result_stored = True

    def get_results(self, name: str) -> List[BenchmarkResult]:
        """Get results by name"""
        return [r for r in self.results if r.name == name]

    def analyze_statistics(self, result: BenchmarkResult) -> Dict[str, Any]:
        """Analyze statistical properties of a benchmark result"""
        if not result.all_times:
            return {}

        times = result.all_times

        # Calculate percentiles
        percentiles = {}
        for p in [25, 50, 75, 90, 95, 99]:
            if len(times) >= 100:
                percentiles[p] = statistics.quantiles(times, n=100)[p - 1]
            else:
                # Approximate percentile for small samples
                idx = int(len(times) * p / 100)
                percentiles[p] = sorted(times)[min(idx, len(times) - 1)]

        # Detect outliers (using IQR method)
        q1 = percentiles[25]
        q3 = percentiles[75]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = [t for t in times if t < lower_bound or t > upper_bound]

        # Calculate confidence interval (95%)
        if len(times) > 1:
            margin = 1.96 * result.std_dev / (len(times) ** 0.5)
            confidence_interval = (result.mean_time - margin, result.mean_time + margin)
        else:
            confidence_interval = (result.mean_time, result.mean_time)

        return {
            "percentiles": percentiles,
            "outliers": outliers,
            "confidence_interval": confidence_interval,
            "variance": result.std_dev ** 2 if result.std_dev else 0,
            "coefficient_of_variation": result.std_dev / result.mean_time if result.mean_time > 0 else 0
        }

    def benchmark_adaptive(
        self,
        func: Callable,
        name: str,
        min_runs: int = 10,
        max_runs: int = 1000,
        confidence_level: float = 0.95,
        args: Tuple = (),
        kwargs: Optional[Dict] = None
    ) -> BenchmarkResult:
        """Adaptive benchmarking that adjusts runs based on variance"""
        if kwargs is None:
            kwargs = {}

        all_times = []

        # Start with minimum runs
        for _ in range(min_runs):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            all_times.append(end - start)

        # Continue until stable or max runs reached
        while len(all_times) < max_runs:
            # Calculate current statistics
            mean = statistics.mean(all_times)
            std = statistics.stdev(all_times) if len(all_times) > 1 else 0

            # Check if variance is low enough
            if std > 0:
                cv = std / mean  # Coefficient of variation
                if cv < 0.05:  # Less than 5% variation
                    break

            # Add more runs
            for _ in range(10):
                start = time.perf_counter()
                func(*args, **kwargs)
                end = time.perf_counter()
                all_times.append(end - start)

        # Calculate final statistics
        mean = statistics.mean(all_times)
        std = statistics.stdev(all_times) if len(all_times) > 1 else 0
        margin = 1.96 * std / (len(all_times) ** 0.5) if std > 0 else 0

        result = BenchmarkResult(
            name=name,
            mean_time=mean,
            min_time=min(all_times),
            max_time=max(all_times),
            std_dev=std,
            all_times=all_times,
            confidence_interval=(mean - margin, mean + margin)
        )

        self.results.append(result)
        return result

    def generate_report(
        self,
        suite: Optional[BenchmarkSuite] = None,
        include_charts: bool = False,
        include_recommendations: bool = False
    ) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        report = {
            "summary": {
                "total_benchmarks": len(self.results),
                "mean_execution_time": statistics.mean([r.mean_time for r in self.results]) if self.results else 0,
            },
            "detailed_results": [
                {
                    "name": r.name,
                    "mean_time": r.mean_time,
                    "min_time": r.min_time,
                    "max_time": r.max_time,
                    "std_dev": r.std_dev
                }
                for r in self.results
            ]
        }

        if include_charts:
            report["charts"] = {
                "execution_times": {
                    "type": "bar",
                    "data": {
                        "labels": [r.name for r in self.results],
                        "values": [r.mean_time for r in self.results]
                    }
                }
            }

        if include_recommendations:
            report["recommendations"] = self._generate_recommendations_for_report()

        return report

    def _generate_recommendations_for_report(self) -> List[str]:
        """Generate recommendations based on all results"""
        if not self.results:
            return ["No results to analyze"]

        recommendations = []

        # Find slowest operations
        slowest = max(self.results, key=lambda r: r.mean_time)
        if slowest.mean_time > 0.1:
            recommendations.append(f"Optimize '{slowest.name}' - it's the slowest operation at {slowest.mean_time:.3f}s")

        # Check for high variance
        high_variance = [r for r in self.results if r.std_dev > r.mean_time * 0.5]
        if high_variance:
            recommendations.append(f"{len(high_variance)} operations have high variance - investigate stability")

        return recommendations if recommendations else ["Performance is within acceptable ranges"]